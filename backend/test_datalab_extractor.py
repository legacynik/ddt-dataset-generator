"""Integration test for Datalab extractor.

This script tests the Datalab extractor with a real PDF from the samples folder.
Run this to verify the Datalab API integration is working correctly.

Usage:
    python test_datalab_extractor.py
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extractors import DatalabExtractor
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_datalab_extraction():
    """Test Datalab extraction with a sample PDF."""

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
    extractor = DatalabExtractor(
        poll_interval=3,
        max_polls=100,
    )

    # Extract
    logger.info("Starting extraction...")
    result = await extractor.extract(pdf_bytes, filename=test_pdf.name)

    # Display results
    print("\n" + "="*80)
    print("DATALAB EXTRACTION RESULTS")
    print("="*80)

    print(f"\nSuccess: {result.success}")
    print(f"Processing time: {result.processing_time_ms}ms ({result.processing_time_ms/1000:.1f}s)")

    if result.error_message:
        print(f"\n❌ Error: {result.error_message}")
        return False

    print(f"\n📄 RAW OCR (first 500 chars):")
    print("-" * 80)
    print(result.raw_ocr[:500])
    if len(result.raw_ocr) > 500:
        print(f"... ({len(result.raw_ocr) - 500} more characters)")

    print(f"\n📊 EXTRACTED JSON:")
    print("-" * 80)
    import json
    print(json.dumps(result.extracted_json, indent=2, ensure_ascii=False))

    print("\n" + "="*80)

    # Validate required fields
    required_fields = ["mittente", "destinatario", "indirizzo_destinazione_completo",
                      "data_documento", "numero_documento"]

    missing_fields = [f for f in required_fields if f not in result.extracted_json]

    if missing_fields:
        logger.warning(f"Missing required fields: {missing_fields}")
    else:
        logger.info("✅ All required fields extracted!")

    return result.success


async def main():
    """Run the test."""
    try:
        logger.info("Starting Datalab extractor integration test")
        logger.info(f"API URL: {settings.DATALAB_API_URL}")
        logger.info(f"API Key: {settings.DATALAB_API_KEY[:10]}...")

        success = await test_datalab_extraction()

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
