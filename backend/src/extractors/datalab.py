"""Datalab API extractor for DDT documents.

This module implements the Datalab extractor which performs:
1. PDF upload to Datalab API
2. Async polling for completion
3. Retrieval of OCR text and structured extraction

Rate limits: 10 requests/minute, max 2 concurrent requests
Polling: 5 second intervals, max 120 polls (10 minutes timeout)
"""

import asyncio
import json
import logging
import time
from typing import Optional
import httpx

from src.config import settings
from src.extractors.schemas import DatalabResult, DDT_EXTRACTION_SCHEMA_JSON

logger = logging.getLogger(__name__)


class DatalabError(Exception):
    """Base exception for Datalab API errors."""
    pass


class DatalabTimeoutError(DatalabError):
    """Raised when polling exceeds maximum attempts."""
    pass


class DatalabRateLimitError(DatalabError):
    """Raised when rate limit is exceeded."""
    pass


class DatalabExtractor:
    """Datalab API client for PDF OCR and structured extraction.

    This extractor submits PDFs to Datalab, polls for completion,
    and retrieves both raw OCR (markdown) and structured JSON data.

    Configuration:
        - API URL: From settings.DATALAB_API_URL
        - API Key: From settings.DATALAB_API_KEY
        - Rate limit: 10 requests/minute
        - Concurrent limit: 2 requests
        - Poll interval: 5 seconds
        - Max polls: 120 (10 minute timeout)

    Example:
        >>> extractor = DatalabExtractor()
        >>> with open("ddt.pdf", "rb") as f:
        ...     result = await extractor.extract(f.read())
        >>> print(result.extracted_json)
    """

    def __init__(
        self,
        poll_interval: int = 5,
        max_polls: int = 120,
        timeout: int = 120,
    ):
        """Initialize Datalab extractor.

        Args:
            poll_interval: Seconds between status polls (default: 5)
            max_polls: Maximum number of poll attempts (default: 120)
            timeout: HTTP request timeout in seconds (default: 120)
        """
        self.api_url = settings.DATALAB_API_URL
        self.api_key = settings.DATALAB_API_KEY
        self.poll_interval = poll_interval
        self.max_polls = max_polls
        self.timeout = timeout

        # Rate limiting
        self._last_request_time = 0.0
        self._min_interval = 6.0  # 10 req/min = 6 seconds between requests

        logger.info(
            f"Initialized DatalabExtractor: "
            f"poll_interval={poll_interval}s, max_polls={max_polls}, "
            f"timeout={timeout}s"
        )

    async def extract(self, pdf_bytes: bytes, filename: str = "document.pdf") -> DatalabResult:
        """Extract DDT data from PDF.

        This method:
        1. Submits PDF to Datalab API with extraction schema
        2. Polls for completion status
        3. Retrieves results (OCR + structured data)

        Args:
            pdf_bytes: PDF file content as bytes
            filename: Original filename (for logging)

        Returns:
            DatalabResult containing OCR text and extracted JSON

        Raises:
            DatalabTimeoutError: If polling exceeds max attempts
            DatalabRateLimitError: If rate limit is hit
            DatalabError: For other API errors
        """
        start_time = time.time()
        logger.info(f"Starting Datalab extraction for {filename} ({len(pdf_bytes)} bytes)")

        try:
            # Step 1: Submit PDF
            request_id = await self._submit_pdf(pdf_bytes, filename)
            logger.info(f"Submitted to Datalab: request_id={request_id}")

            # Step 2: Poll for completion
            result_data = await self._poll_for_completion(request_id, filename)

            # Step 3: Parse results
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Get markdown output
            raw_ocr = result_data.get("markdown", "")

            # Get structured extraction from extraction_schema_json field
            # When page_schema is provided, extracted data is in this field (as a JSON string)
            extracted_json = {}
            extraction_schema_json_str = result_data.get("extraction_schema_json", "{}")

            # Parse the JSON string
            try:
                extracted_json = json.loads(extraction_schema_json_str) if extraction_schema_json_str else {}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse extraction_schema_json for {filename}: {e}")
                # Keep extracted_json as empty dict
                extracted_json = {}

            logger.info(
                f"Datalab extraction completed for {filename}: "
                f"ocr_length={len(raw_ocr)}, "
                f"fields_extracted={len(extracted_json)}, "
                f"time={processing_time_ms}ms"
            )

            return DatalabResult(
                raw_ocr=raw_ocr,
                extracted_json=extracted_json,
                processing_time_ms=processing_time_ms,
                success=True,
                error_message=None,
            )

        except DatalabTimeoutError as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Datalab timeout for {filename}: {e}")
            return DatalabResult(
                raw_ocr="",
                extracted_json={},
                processing_time_ms=processing_time_ms,
                success=False,
                error_message=f"Timeout after {self.max_polls} polls: {str(e)}",
            )

        except DatalabRateLimitError as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Datalab rate limit for {filename}: {e}")
            return DatalabResult(
                raw_ocr="",
                extracted_json={},
                processing_time_ms=processing_time_ms,
                success=False,
                error_message=f"Rate limit exceeded: {str(e)}",
            )

        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Datalab extraction failed for {filename}: {e}", exc_info=True)
            return DatalabResult(
                raw_ocr="",
                extracted_json={},
                processing_time_ms=processing_time_ms,
                success=False,
                error_message=str(e),
            )

    async def _submit_pdf(self, pdf_bytes: bytes, filename: str) -> str:
        """Submit PDF to Datalab API.

        Args:
            pdf_bytes: PDF content
            filename: Original filename

        Returns:
            Request ID for polling

        Raises:
            DatalabError: If submission fails
        """
        await self._rate_limit()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Prepare multipart form data (Datalab format)
                files = {
                    "file": (filename, pdf_bytes, "application/pdf"),
                }

                # Data parameters
                data = {
                    "output_format": "markdown,json",
                    "mode": "accurate",  # Use accurate mode for best DDT extraction
                    "paginate": "false",
                    "disable_image_extraction": "false",
                    "page_schema": DDT_EXTRACTION_SCHEMA_JSON,  # Structured extraction schema
                }

                headers = {
                    "X-Api-Key": self.api_key,  # Datalab uses X-Api-Key, not Bearer token
                }

                response = await client.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    data=data,
                )

                # Handle rate limit
                if response.status_code == 429:
                    raise DatalabRateLimitError(
                        f"Rate limit exceeded: {response.text}"
                    )

                response.raise_for_status()
                result = response.json()

                request_id = result.get("request_id")
                if not request_id:
                    raise DatalabError(f"No request_id in response: {result}")

                return request_id

            except httpx.HTTPStatusError as e:
                raise DatalabError(f"HTTP error submitting PDF: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                raise DatalabError(f"Network error submitting PDF: {str(e)}")

    async def _poll_for_completion(self, request_id: str, filename: str) -> dict:
        """Poll Datalab API until processing completes.

        Args:
            request_id: Request ID from submission
            filename: Original filename (for logging)

        Returns:
            Result data containing markdown and extracted_data

        Raises:
            DatalabTimeoutError: If max polls exceeded
            DatalabError: For API errors
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, self.max_polls + 1):
                await asyncio.sleep(self.poll_interval)
                await self._rate_limit()

                try:
                    headers = {
                        "X-Api-Key": self.api_key,  # Use X-Api-Key for polling too
                    }

                    # Use request_check_url from response
                    status_url = f"{self.api_url}/{request_id}"
                    response = await client.get(status_url, headers=headers)

                    # Handle rate limit
                    if response.status_code == 429:
                        logger.warning(f"Rate limit on poll attempt {attempt}, will retry")
                        await asyncio.sleep(10)  # Extra delay on rate limit
                        continue

                    response.raise_for_status()
                    result = response.json()

                    status = result.get("status")

                    if status == "complete":  # Datalab uses "complete" not "completed"
                        logger.info(f"Datalab completed after {attempt} polls ({attempt * self.poll_interval}s)")
                        return result

                    elif status == "failed":
                        error_msg = result.get("error", "Unknown error")
                        raise DatalabError(f"Datalab processing failed: {error_msg}")

                    elif status in ["pending", "processing"]:
                        if attempt % 10 == 0:  # Log every 30 seconds
                            logger.info(
                                f"Datalab still processing {filename}: "
                                f"poll {attempt}/{self.max_polls} ({attempt * self.poll_interval}s elapsed)"
                            )
                        continue

                    else:
                        logger.warning(f"Unknown Datalab status: {status}")
                        continue

                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error polling (attempt {attempt}): {e.response.status_code}")
                    if attempt >= self.max_polls:
                        raise DatalabError(f"Polling failed: {e.response.text}")
                    await asyncio.sleep(5)  # Wait before retry

                except httpx.RequestError as e:
                    logger.error(f"Network error polling (attempt {attempt}): {str(e)}")
                    if attempt >= self.max_polls:
                        raise DatalabError(f"Network error: {str(e)}")
                    await asyncio.sleep(5)  # Wait before retry

        # Max polls exceeded
        raise DatalabTimeoutError(
            f"Polling timeout after {self.max_polls} attempts "
            f"({self.max_polls * self.poll_interval} seconds)"
        )

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests.

        Ensures minimum interval of 6 seconds between requests
        (10 requests/minute = 6 seconds per request).
        """
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self._min_interval:
            wait_time = self._min_interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self._last_request_time = time.time()
