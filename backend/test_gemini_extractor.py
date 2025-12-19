"""Integration test for Gemini extractor.

This script tests the Gemini extractor with sample OCR text.
Run this to verify the Gemini API integration is working correctly.

Usage:
    python test_gemini_extractor.py
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extractors import GeminiExtractor
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Sample OCR text from a typical Italian DDT
SAMPLE_OCR_TEXT = """
DOCUMENTO DI TRASPORTO N. 2025/001

MITTENTE:
BARILLA G. e R. FRATELLI S.p.A.
Via Mantova, 166
43122 Parma (PR)
P.IVA: 01654010345

DESTINATARIO MERCE:
COOP ITALIA SOC. COOP.
Destinazione: Via Roma 123
20100 Milano (MI)

CAUSALE TRASPORTO: Vendita
DATA DOCUMENTO: 15/01/2025
DATA INIZIO TRASPORTO: 16/01/2025

ORDINE CLIENTE: ORD-2024-5678
CODICE CLIENTE: CLI-001234

DESCRIZIONE MERCE:
- Pasta Barilla Spaghetti n.5
- Quantità: 500 kg
- Colli: 50

TRASPORTATORE:
Logistica Express S.r.l.

Note: Consegna urgente
"""


async def test_gemini_extraction():
    """Test Gemini extraction with sample OCR text."""

    logger.info(f"Testing with sample OCR text ({len(SAMPLE_OCR_TEXT)} chars)")

    # Create extractor
    extractor = GeminiExtractor(
        max_retries=2,
        timeout=60,
    )

    # Extract
    logger.info("Starting extraction...")
    result = await extractor.extract(SAMPLE_OCR_TEXT, filename="sample_ddt.txt")

    # Display results
    print("\n" + "="*80)
    print("GEMINI EXTRACTION RESULTS")
    print("="*80)

    print(f"\nSuccess: {result.success}")
    print(f"Processing time: {result.processing_time_ms}ms ({result.processing_time_ms/1000:.1f}s)")

    if result.error_message:
        print(f"\n❌ Error: {result.error_message}")
        return False

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
        print(f"\n⚠️  Missing fields: {missing_fields}")
    else:
        logger.info("✅ All required fields extracted!")
        print("\n✅ All required fields present!")

    # Validate extracted values
    expected_values = {
        "mittente": "BARILLA G. e R. FRATELLI S.p.A.",
        "destinatario": "COOP ITALIA SOC. COOP.",
        "numero_documento": "2025/001",
        "data_documento": "2025-01-15",
    }

    print(f"\n📋 VALIDATION:")
    print("-" * 80)
    for field, expected in expected_values.items():
        actual = result.extracted_json.get(field)
        match = "✅" if actual and expected.lower() in str(actual).lower() else "⚠️ "
        print(f"{match} {field}: {actual}")

    return result.success


async def main():
    """Run the test."""
    try:
        logger.info("Starting Gemini extractor integration test")
        logger.info(f"Model: {settings.GEMINI_MODEL}")
        logger.info(f"API Key: {settings.GOOGLE_API_KEY[:20]}...")

        success = await test_gemini_extraction()

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
