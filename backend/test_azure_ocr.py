"""Integration test for Azure OCR extractor.

This script tests the Azure Document Intelligence OCR extractor with a real PDF.
Run this to verify the Azure integration is working correctly.

Usage:
    python test_azure_ocr.py
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extractors import AzureOCRExtractor
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_azure_ocr():
    """Test Azure OCR extraction with a sample PDF."""

    # Find first sample PDF
    samples_dir = Path(__file__).parent.parent / "samples"
    pdf_files = list(samples_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error(f"No PDF files found in {samples_dir}")
        return False

    test_pdf = pdf_files[0]
    logger.info(f"Testing with: {test_pdf.name} ({test_pdf.stat().st_size} bytes)")

    # Read PDF
    with open(test_pdf, "rb") as f:
        pdf_bytes = f.read()

    # Create extractor
    extractor = AzureOCRExtractor(
        timeout=60,
        max_retries=3,
        retry_delay=5,
    )

    # Extract
    logger.info("Starting OCR extraction...")
    result = await extractor.extract(pdf_bytes, filename=test_pdf.name)

    # Display results
    print("\n" + "="*80)
    print("AZURE OCR EXTRACTION RESULTS")
    print("="*80)

    print(f"\nSuccess: {result.success}")
    print(f"Processing time: {result.processing_time_ms}ms ({result.processing_time_ms/1000:.1f}s)")

    if result.error_message:
        print(f"\n❌ Error: {result.error_message}")
        return False

    print(f"\n📄 EXTRACTED TEXT:")
    print(f"Total length: {len(result.raw_text)} characters")
    print("-" * 80)
    print(result.raw_text[:1000])
    if len(result.raw_text) > 1000:
        print(f"... ({len(result.raw_text) - 1000} more characters)")

    print("\n" + "="*80)

    # Basic validation
    if len(result.raw_text) < 50:
        logger.warning("⚠️  Text seems too short, might be empty or failed")
        return False
    else:
        logger.info(f"✅ OCR extraction successful! Extracted {len(result.raw_text)} characters")

    return result.success


async def main():
    """Run the test."""
    try:
        logger.info("Starting Azure OCR extractor integration test")
        logger.info(f"Endpoint: {settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT}")
        logger.info(f"API Key: {settings.AZURE_DOCUMENT_INTELLIGENCE_KEY[:20]}...")

        success = await test_azure_ocr()

        if success:
            logger.info("✅ Test PASSED")
            sys.exit(0)
        else:
            logger.error("❌ Test FAILED")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
