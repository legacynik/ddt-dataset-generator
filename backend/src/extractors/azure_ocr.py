"""Azure Document Intelligence OCR extractor with Layout model.

This module implements OCR extraction using Azure Document Intelligence
with the prebuilt-layout model and markdown output format.

The Layout model extracts:
- Structured text with paragraphs
- Tables in HTML format (<table>, <tr>, <td>)
- Figures with <figure> tags
- Checkboxes with Unicode symbols (☐ ☒)
- Page headers/footers as HTML comments

This provides ~2.5x richer output compared to prebuilt-read model,
which is essential for DDT documents with complex table structures.

Rate limits: 1 request/second, max 2 concurrent requests
Timeout: 120 seconds per request (layout takes longer than read)
Retries: 3 attempts on 429 rate limit errors

API Version: 2024-11-30 (latest with markdown support)

See also: azure_ocr_read.py for the simpler prebuilt-read model ($1.50/1k vs $10/1k)
"""

import asyncio
import logging
import time
from typing import Optional
import aiohttp

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
    """Azure Document Intelligence Layout extractor with markdown output.

    Uses Azure's prebuilt-layout model to extract structured text from PDFs.
    Output is in markdown format with HTML tables, figures, and checkboxes.

    This provides much richer structure than the prebuilt-read model:
    - Tables are extracted as HTML (<table>, <tr>, <td>)
    - Figures are wrapped in <figure> tags
    - Checkboxes use Unicode: ☐ (unchecked), ☒ (checked)
    - Page info as HTML comments: <!-- PageHeader="..." -->

    Configuration:
        - Endpoint: From settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        - API Key: From settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
        - Model: prebuilt-layout (vs prebuilt-read in azure_ocr_read.py)
        - Output: Markdown format
        - API Version: 2024-11-30
        - Rate limit: 1 request/second
        - Timeout: 120 seconds (layout is slower than read)
        - Retries: 3 on 429 errors

    Pricing:
        - prebuilt-layout: $10.00 / 1,000 pages
        - prebuilt-read: $1.50 / 1,000 pages (see azure_ocr_read.py)

    Example:
        >>> extractor = AzureOCRExtractor()
        >>> with open("ddt.pdf", "rb") as f:
        ...     result = await extractor.extract(f.read())
        >>> print(result.raw_text)  # Contains markdown with HTML tables
    """

    # API version with markdown support
    API_VERSION = "2024-11-30"
    MODEL_ID = "prebuilt-layout"

    def __init__(
        self,
        timeout: int = 120,  # Layout takes longer than read
        max_retries: int = 3,
        retry_delay: int = 5,
        poll_interval: int = 2,
        max_polls: int = 60,  # 60 polls * 2s = 120s max wait
    ):
        """Initialize Azure OCR Layout extractor.

        Args:
            timeout: HTTP request timeout in seconds (default: 120)
            max_retries: Maximum retry attempts on 429 (default: 3)
            retry_delay: Delay between retries in seconds (default: 5)
            poll_interval: Seconds between polling attempts (default: 2)
            max_polls: Maximum polling attempts (default: 60)
        """
        self.endpoint = settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        self.api_key = settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.poll_interval = poll_interval
        self.max_polls = max_polls

        # Rate limiting: 1 req/sec
        self._last_request_time = 0.0
        self._min_interval = 1.0

        # Build API URL
        self.analyze_url = (
            f"{self.endpoint}/documentintelligence/documentModels/{self.MODEL_ID}:analyze"
            f"?api-version={self.API_VERSION}&outputContentFormat=markdown"
        )

        logger.info(
            f"Initialized AzureOCRExtractor (Layout+Markdown): "
            f"endpoint={self.endpoint}, model={self.MODEL_ID}, "
            f"api_version={self.API_VERSION}, timeout={timeout}s, "
            f"max_retries={max_retries}"
        )

    async def extract(self, pdf_bytes: bytes, filename: str = "document.pdf") -> AzureOCRResult:
        """Extract structured text from PDF using Azure Document Intelligence Layout.

        This method:
        1. Submits PDF to Azure Document Intelligence (Layout model)
        2. Polls for analysis completion
        3. Extracts markdown content with HTML tables
        4. Returns structured text with table/figure markup

        Args:
            pdf_bytes: PDF file content as bytes
            filename: Original filename (for logging)

        Returns:
            AzureOCRResult containing markdown-formatted OCR text with:
            - HTML tables (<table>, <tr>, <td>)
            - Figure tags (<figure>)
            - Checkbox Unicode (☐ ☒)
            - Paragraph structure
        """
        start_time = time.time()
        logger.info(f"Starting Azure Layout OCR for {filename} ({len(pdf_bytes)} bytes)")

        retry_count = 0

        while retry_count <= self.max_retries:
            try:
                # Rate limiting
                await self._rate_limit()

                # Submit document for analysis
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Ocp-Apim-Subscription-Key": self.api_key,
                        "Content-Type": "application/pdf",
                    }

                    logger.debug(f"Submitting {filename} to Azure Layout (attempt {retry_count + 1})")

                    async with session.post(
                        self.analyze_url,
                        headers=headers,
                        data=pdf_bytes,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ) as response:
                        if response.status == 429:
                            # Rate limited
                            retry_count += 1
                            if retry_count <= self.max_retries:
                                wait_time = self.retry_delay * retry_count
                                logger.warning(
                                    f"Azure rate limit (429) for {filename}, "
                                    f"retry {retry_count}/{self.max_retries} after {wait_time}s"
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                processing_time_ms = int((time.time() - start_time) * 1000)
                                return AzureOCRResult(
                                    raw_text="",
                                    processing_time_ms=processing_time_ms,
                                    success=False,
                                    error_message=f"Rate limit exceeded after {self.max_retries} retries",
                                )

                        if response.status != 202:
                            error_text = await response.text()
                            processing_time_ms = int((time.time() - start_time) * 1000)
                            logger.error(f"Azure Layout error for {filename}: {response.status} - {error_text}")
                            return AzureOCRResult(
                                raw_text="",
                                processing_time_ms=processing_time_ms,
                                success=False,
                                error_message=f"HTTP {response.status}: {error_text[:200]}",
                            )

                        # Get operation location for polling
                        operation_url = response.headers.get("Operation-Location")
                        if not operation_url:
                            processing_time_ms = int((time.time() - start_time) * 1000)
                            return AzureOCRResult(
                                raw_text="",
                                processing_time_ms=processing_time_ms,
                                success=False,
                                error_message="No Operation-Location header in response",
                            )

                    # Poll for result
                    logger.debug(f"Polling for {filename} result...")
                    result = await self._poll_for_result(session, operation_url, filename)

                    if result is None:
                        processing_time_ms = int((time.time() - start_time) * 1000)
                        return AzureOCRResult(
                            raw_text="",
                            processing_time_ms=processing_time_ms,
                            success=False,
                            error_message=f"Timeout after {self.max_polls} polls",
                        )

                    # Extract content
                    status = result.get("status")
                    if status == "succeeded":
                        analyze_result = result.get("analyzeResult", {})
                        content = analyze_result.get("content", "")
                        tables_count = len(analyze_result.get("tables", []))
                        paragraphs_count = len(analyze_result.get("paragraphs", []))

                        processing_time_ms = int((time.time() - start_time) * 1000)

                        logger.info(
                            f"Azure Layout OCR completed for {filename}: "
                            f"content_length={len(content)}, "
                            f"tables={tables_count}, paragraphs={paragraphs_count}, "
                            f"time={processing_time_ms}ms"
                        )

                        return AzureOCRResult(
                            raw_text=content,
                            processing_time_ms=processing_time_ms,
                            success=True,
                            error_message=None,
                        )
                    else:
                        error_info = result.get("error", {})
                        error_message = error_info.get("message", f"Analysis failed with status: {status}")
                        processing_time_ms = int((time.time() - start_time) * 1000)
                        logger.error(f"Azure Layout failed for {filename}: {error_message}")
                        return AzureOCRResult(
                            raw_text="",
                            processing_time_ms=processing_time_ms,
                            success=False,
                            error_message=error_message,
                        )

            except aiohttp.ClientError as e:
                processing_time_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Azure Layout HTTP error for {filename}: {e}", exc_info=True)
                return AzureOCRResult(
                    raw_text="",
                    processing_time_ms=processing_time_ms,
                    success=False,
                    error_message=str(e),
                )

            except Exception as e:
                processing_time_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Azure Layout OCR failed for {filename}: {e}", exc_info=True)
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

    async def _poll_for_result(
        self,
        session: aiohttp.ClientSession,
        operation_url: str,
        filename: str,
    ) -> Optional[dict]:
        """Poll for analysis result.

        Args:
            session: aiohttp session
            operation_url: URL to poll for result
            filename: For logging

        Returns:
            Result dict if succeeded/failed, None if timeout
        """
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}

        for poll_num in range(self.max_polls):
            await asyncio.sleep(self.poll_interval)

            try:
                async with session.get(
                    operation_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Poll error for {filename}: {response.status}"
                        )
                        continue

                    result = await response.json()
                    status = result.get("status")

                    if status in ("succeeded", "failed"):
                        return result

                    if poll_num % 5 == 0:  # Log every 5 polls
                        logger.debug(
                            f"Azure Layout still processing {filename}: "
                            f"poll {poll_num + 1}/{self.max_polls}"
                        )

            except Exception as e:
                logger.warning(f"Poll error for {filename}: {e}")
                continue

        logger.error(f"Azure Layout timeout for {filename} after {self.max_polls} polls")
        return None

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests.

        Ensures minimum interval of 1 second between requests.
        """
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self._min_interval:
            wait_time = self._min_interval - elapsed
            logger.debug(f"Azure rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self._last_request_time = time.time()
