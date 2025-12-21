"""Azure Document Intelligence OCR extractor.

This module implements OCR extraction using Azure Document Intelligence
(formerly Azure Form Recognizer) with the prebuilt-read model.

Rate limits: 1 request/second, max 2 concurrent requests
Timeout: 60 seconds per request
Retries: 3 attempts on 429 rate limit errors
"""

import asyncio
import logging
import time
from typing import Optional
from io import BytesIO

from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from src.config import settings
from src.extractors.schemas import AzureOCRResult

logger = logging.getLogger(__name__)


class AzureOCRError(Exception):
    """Base exception for Azure OCR errors."""
    pass


class AzureRateLimitError(AzureOCRError):
    """Raised when Azure rate limit is exceeded."""
    pass


class AzureOCRExtractor:
    """Azure Document Intelligence OCR extractor.

    Uses Azure's prebuilt-read model to extract raw text from PDFs.
    This provides high-quality OCR that will be used as input for
    Gemini structured extraction.

    Configuration:
        - Endpoint: From settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        - API Key: From settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
        - Rate limit: 1 request/second
        - Concurrent limit: 2 requests
        - Timeout: 60 seconds
        - Retries: 3 on 429 errors

    Example:
        >>> extractor = AzureOCRExtractor()
        >>> with open("ddt.pdf", "rb") as f:
        ...     result = await extractor.extract(f.read())
        >>> print(result.raw_text)
    """

    def __init__(
        self,
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """Initialize Azure OCR extractor.

        Args:
            timeout: Request timeout in seconds (default: 60)
            max_retries: Maximum retry attempts on 429 (default: 3)
            retry_delay: Delay between retries in seconds (default: 5)
        """
        self.endpoint = settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        self.credential = AzureKeyCredential(settings.AZURE_DOCUMENT_INTELLIGENCE_KEY)
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Rate limiting: 1 req/sec
        self._last_request_time = 0.0
        self._min_interval = 1.0  # 1 second between requests

        logger.info(
            f"Initialized AzureOCRExtractor: "
            f"endpoint={self.endpoint}, timeout={timeout}s, "
            f"max_retries={max_retries}"
        )

    async def extract(self, pdf_bytes: bytes, filename: str = "document.pdf") -> AzureOCRResult:
        """Extract text from PDF using Azure Document Intelligence.

        This method:
        1. Submits PDF to Azure Document Intelligence
        2. Waits for analysis to complete
        3. Extracts all text content
        4. Returns raw text

        Args:
            pdf_bytes: PDF file content as bytes
            filename: Original filename (for logging)

        Returns:
            AzureOCRResult containing raw OCR text

        Raises:
            AzureOCRError: For API errors (wrapped, not raised)
        """
        start_time = time.time()
        logger.info(f"Starting Azure OCR for {filename} ({len(pdf_bytes)} bytes)")

        retry_count = 0

        while retry_count <= self.max_retries:
            try:
                # Rate limiting
                await self._rate_limit()

                # Create client (async context manager)
                async with DocumentAnalysisClient(
                    endpoint=self.endpoint,
                    credential=self.credential,
                ) as client:
                    # Submit document for analysis
                    logger.debug(f"Submitting {filename} to Azure (attempt {retry_count + 1})")

                    # Use prebuilt-read model
                    poller = await client.begin_analyze_document(
                        model_id="prebuilt-read",
                        document=BytesIO(pdf_bytes),
                    )

                    # Wait for completion
                    result = await poller.result()

                    # Extract text content
                    raw_text = self._extract_text(result)

                    processing_time_ms = int((time.time() - start_time) * 1000)

                    logger.info(
                        f"Azure OCR completed for {filename}: "
                        f"text_length={len(raw_text)}, "
                        f"pages={len(result.pages)}, "
                        f"time={processing_time_ms}ms"
                    )

                    return AzureOCRResult(
                        raw_text=raw_text,
                        processing_time_ms=processing_time_ms,
                        success=True,
                        error_message=None,
                    )

            except HttpResponseError as e:
                # Handle rate limiting (429)
                if e.status_code == 429:
                    retry_count += 1
                    if retry_count <= self.max_retries:
                        wait_time = self.retry_delay * retry_count  # Exponential backoff
                        logger.warning(
                            f"Azure rate limit (429) for {filename}, "
                            f"retry {retry_count}/{self.max_retries} after {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        processing_time_ms = int((time.time() - start_time) * 1000)
                        logger.error(f"Azure rate limit exceeded for {filename} after {self.max_retries} retries")
                        return AzureOCRResult(
                            raw_text="",
                            processing_time_ms=processing_time_ms,
                            success=False,
                            error_message=f"Rate limit exceeded after {self.max_retries} retries: {str(e)}",
                        )

                # Other HTTP errors
                processing_time_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Azure HTTP error for {filename}: {e.status_code} - {e.message}")
                return AzureOCRResult(
                    raw_text="",
                    processing_time_ms=processing_time_ms,
                    success=False,
                    error_message=f"HTTP {e.status_code}: {e.message}",
                )

            except Exception as e:
                processing_time_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Azure OCR failed for {filename}: {e}", exc_info=True)
                return AzureOCRResult(
                    raw_text="",
                    processing_time_ms=processing_time_ms,
                    success=False,
                    error_message=str(e),
                )

        # Should not reach here
        processing_time_ms = int((time.time() - start_time) * 1000)
        return AzureOCRResult(
            raw_text="",
            processing_time_ms=processing_time_ms,
            success=False,
            error_message="Unexpected error in retry loop",
        )

    def _extract_text(self, result) -> str:
        """Extract all text from Azure analysis result.

        Concatenates text from all pages in reading order.

        Args:
            result: Azure DocumentAnalysisResult

        Returns:
            Raw text content
        """
        text_parts = []

        # Extract text page by page
        for page in result.pages:
            page_text = []

            # Get lines in reading order
            if hasattr(page, 'lines') and page.lines:
                for line in page.lines:
                    page_text.append(line.content)

            # Join lines with newlines
            if page_text:
                text_parts.append("\n".join(page_text))

        # Join pages with double newlines
        full_text = "\n\n".join(text_parts)

        return full_text.strip()

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests.

        Ensures minimum interval of 1 second between requests
        (1 request/second).
        """
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self._min_interval:
            wait_time = self._min_interval - elapsed
            logger.debug(f"Azure rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self._last_request_time = time.time()
