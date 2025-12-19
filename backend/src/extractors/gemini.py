"""Gemini extractor for DDT structured data extraction.

This module implements structured extraction using Google Gemini models.
It takes OCR text as input and extracts structured DDT data as JSON.

Rate limits: 10 requests/minute, max 2 concurrent requests
Retries: 2 attempts on JSON parse errors
Timeout: 60 seconds per request
"""

import asyncio
import json
import logging
import time
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from src.config import settings
from src.extractors.schemas import GeminiResult, DDT_EXTRACTION_SCHEMA

logger = logging.getLogger(__name__)


# System prompt for Gemini (from PRD)
GEMINI_SYSTEM_PROMPT = """Sei un assistente specializzato nell'estrazione dati da Documenti di Trasporto (DDT) italiani.

REGOLE:
1. Estrai SOLO i dati richiesti, non inventare informazioni mancanti
2. Se un campo non è presente nel documento, restituisci null
3. Per le date, converti sempre in formato YYYY-MM-DD
4. Per mittente e destinatario, estrai SOLO la ragione sociale (nome azienda), MAI l'indirizzo
5. Non confondere il Vettore/Trasportatore con il Mittente
6. Se ci sono più indirizzi, dai priorità a "Destinazione Merce" rispetto a "Sede Legale"

Rispondi ESCLUSIVAMENTE con JSON valido, senza markdown, senza spiegazioni."""


class GeminiError(Exception):
    """Base exception for Gemini extractor errors."""
    pass


class GeminiRateLimitError(GeminiError):
    """Raised when Gemini rate limit is exceeded."""
    pass


class GeminiJSONError(GeminiError):
    """Raised when Gemini returns invalid JSON."""
    pass


class GeminiExtractor:
    """Gemini extractor for DDT structured data extraction.

    This extractor takes OCR text and uses Google Gemini to extract
    structured DDT data according to the schema defined in DDT_EXTRACTION_SCHEMA.

    Configuration:
        - Model: From settings.GEMINI_MODEL (default: gemini-1.5-flash)
        - API Key: From settings.GOOGLE_API_KEY
        - Rate limit: 10 requests/minute
        - Concurrent limit: 2 requests
        - Max retries: 2 on JSON parse errors
        - Timeout: 60 seconds

    Example:
        >>> extractor = GeminiExtractor()
        >>> ocr_text = "DDT N. 123\\nMittente: LAVAZZA..."
        >>> result = await extractor.extract(ocr_text)
        >>> print(result.extracted_json)
    """

    def __init__(
        self,
        max_retries: int = 2,
        timeout: int = 60,
    ):
        """Initialize Gemini extractor.

        Args:
            max_retries: Maximum retry attempts on JSON errors (default: 2)
            timeout: Request timeout in seconds (default: 60)
        """
        # Configure Gemini API
        genai.configure(api_key=settings.GOOGLE_API_KEY)

        self.model_name = settings.GEMINI_MODEL
        self.max_retries = max_retries
        self.timeout = timeout

        # Initialize model with generation config
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.1,  # Low temperature for consistent extraction
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json",  # JSON mode
            },
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
        )

        # Rate limiting: 10 req/min = 6 seconds per request
        self._last_request_time = 0.0
        self._min_interval = 6.0

        logger.info(
            f"Initialized GeminiExtractor: "
            f"model={self.model_name}, max_retries={max_retries}, "
            f"timeout={timeout}s"
        )

    async def extract(self, ocr_text: str, filename: str = "document") -> GeminiResult:
        """Extract structured DDT data from OCR text.

        This method:
        1. Constructs prompt with system instructions + OCR text
        2. Calls Gemini API with JSON mode
        3. Parses and validates JSON response
        4. Retries on JSON parse errors

        Args:
            ocr_text: Raw OCR text from Azure or Datalab
            filename: Original filename (for logging)

        Returns:
            GeminiResult containing extracted JSON

        Raises:
            GeminiError: For API errors (wrapped, not raised)
        """
        start_time = time.time()
        logger.info(f"Starting Gemini extraction for {filename} ({len(ocr_text)} chars)")

        # Try extraction with retries
        for attempt in range(1, self.max_retries + 2):  # +1 for initial attempt
            try:
                await self._rate_limit()

                # Construct prompt
                prompt = self._build_prompt(ocr_text)

                # Call Gemini API
                logger.debug(f"Calling Gemini (attempt {attempt})")

                # Run in executor since Gemini SDK is sync
                response = await asyncio.wait_for(
                    asyncio.to_thread(self._generate_content, prompt),
                    timeout=self.timeout
                )

                # Parse response
                response_text = response.text.strip()
                logger.debug(f"Gemini response: {response_text[:200]}...")

                # Parse JSON
                try:
                    extracted_json = json.loads(response_text)
                except json.JSONDecodeError as e:
                    if attempt <= self.max_retries:
                        logger.warning(
                            f"JSON parse error for {filename} (attempt {attempt}), retrying: {e}"
                        )
                        await asyncio.sleep(2 * attempt)  # Exponential backoff
                        continue
                    else:
                        raise GeminiJSONError(f"Invalid JSON after {self.max_retries} retries: {e}")

                # Success
                processing_time_ms = int((time.time() - start_time) * 1000)

                logger.info(
                    f"Gemini extraction completed for {filename}: "
                    f"fields={len(extracted_json)}, "
                    f"time={processing_time_ms}ms"
                )

                return GeminiResult(
                    extracted_json=extracted_json,
                    processing_time_ms=processing_time_ms,
                    success=True,
                    error_message=None,
                )

            except asyncio.TimeoutError:
                processing_time_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Gemini timeout for {filename} after {self.timeout}s")
                return GeminiResult(
                    extracted_json={},
                    processing_time_ms=processing_time_ms,
                    success=False,
                    error_message=f"Timeout after {self.timeout}s",
                )

            except GeminiJSONError as e:
                processing_time_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Gemini JSON error for {filename}: {e}")
                return GeminiResult(
                    extracted_json={},
                    processing_time_ms=processing_time_ms,
                    success=False,
                    error_message=str(e),
                )

            except Exception as e:
                processing_time_ms = int((time.time() - start_time) * 1000)
                error_msg = str(e)

                # Check for rate limit
                if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                    logger.error(f"Gemini rate limit for {filename}: {e}")
                    return GeminiResult(
                        extracted_json={},
                        processing_time_ms=processing_time_ms,
                        success=False,
                        error_message=f"Rate limit exceeded: {error_msg}",
                    )

                logger.error(f"Gemini extraction failed for {filename}: {e}", exc_info=True)
                return GeminiResult(
                    extracted_json={},
                    processing_time_ms=processing_time_ms,
                    success=False,
                    error_message=error_msg,
                )

        # Should not reach here
        processing_time_ms = int((time.time() - start_time) * 1000)
        return GeminiResult(
            extracted_json={},
            processing_time_ms=processing_time_ms,
            success=False,
            error_message="Unexpected error in retry loop",
        )

    def _generate_content(self, prompt: str):
        """Synchronous call to Gemini API.

        This method is run in a thread executor to make it async-compatible.

        Args:
            prompt: Full prompt with instructions and OCR text

        Returns:
            Gemini response object
        """
        return self.model.generate_content(prompt)

    def _build_prompt(self, ocr_text: str) -> str:
        """Build complete prompt for Gemini.

        Combines system instructions, schema, and OCR text.

        Args:
            ocr_text: Raw OCR text

        Returns:
            Complete prompt string
        """
        # Include schema in prompt for better context
        schema_desc = self._format_schema_description()

        prompt = f"""{GEMINI_SYSTEM_PROMPT}

SCHEMA DEI CAMPI DA ESTRARRE:
{schema_desc}

TESTO OCR DEL DOCUMENTO:
{ocr_text}

Estrai i dati e rispondi con JSON valido contenente i campi richiesti."""

        return prompt

    def _format_schema_description(self) -> str:
        """Format schema as readable description for the prompt.

        Returns:
            Formatted schema description
        """
        lines = []
        for field, spec in DDT_EXTRACTION_SCHEMA["properties"].items():
            required = " (OBBLIGATORIO)" if field in DDT_EXTRACTION_SCHEMA.get("required", []) else " (opzionale)"
            lines.append(f"- {field}{required}: {spec['description']}")

        return "\n".join(lines)

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests.

        Ensures minimum interval of 6 seconds between requests
        (10 requests/minute = 6 seconds per request).
        """
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self._min_interval:
            wait_time = self._min_interval - elapsed
            logger.debug(f"Gemini rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self._last_request_time = time.time()
