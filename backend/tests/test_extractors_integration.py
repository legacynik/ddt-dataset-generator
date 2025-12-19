"""Integration tests for Azure OCR and Gemini extractors.

Tests with real API keys and sample PDF to verify:
1. Azure Document Intelligence OCR extraction
2. Gemini structured extraction from OCR text
3. Full pipeline flow
"""

import pytest
import asyncio
from pathlib import Path

from src.extractors import AzureOCRExtractor, GeminiExtractor
from src.config import settings


# Sample PDF path
SAMPLE_PDF_PATH = Path(__file__).parent.parent.parent / "samples" / "testScansione1.pdf"


@pytest.mark.asyncio
async def test_azure_ocr_extraction():
    """Test Azure OCR extraction with real API."""
    if not SAMPLE_PDF_PATH.exists():
        pytest.skip(f"Sample PDF not found: {SAMPLE_PDF_PATH}")

    # Read PDF bytes
    pdf_bytes = SAMPLE_PDF_PATH.read_bytes()

    # Initialize Azure extractor
    azure = AzureOCRExtractor(timeout=60, max_retries=3)

    # Extract OCR text
    result = await azure.extract(pdf_bytes, SAMPLE_PDF_PATH.name)

    # Assertions
    assert result is not None, "Azure result should not be None"
    assert result.success, f"Azure extraction should succeed. Error: {result.error_message}"
    assert result.raw_text, "Azure raw_text should not be empty"
    assert len(result.raw_text) > 100, "Azure OCR should extract substantial text"
    assert result.processing_time_ms > 0, "Processing time should be positive"

    print(f"\n✓ Azure OCR extraction successful")
    print(f"  - Processing time: {result.processing_time_ms}ms")
    print(f"  - Text length: {len(result.raw_text)} chars")
    print(f"  - First 200 chars: {result.raw_text[:200]}...")

    return result


@pytest.mark.asyncio
async def test_gemini_extraction_from_azure():
    """Test Gemini extraction using Azure OCR output."""
    if not SAMPLE_PDF_PATH.exists():
        pytest.skip(f"Sample PDF not found: {SAMPLE_PDF_PATH}")

    # Step 1: Get Azure OCR
    pdf_bytes = SAMPLE_PDF_PATH.read_bytes()
    azure = AzureOCRExtractor(timeout=60, max_retries=3)
    azure_result = await azure.extract(pdf_bytes, SAMPLE_PDF_PATH.name)

    assert azure_result.success, "Azure extraction must succeed for Gemini test"

    # Step 2: Run Gemini on Azure text
    gemini = GeminiExtractor(max_retries=2, timeout=60)
    gemini_result = await gemini.extract(azure_result.raw_text, SAMPLE_PDF_PATH.name)

    # Assertions
    assert gemini_result is not None, "Gemini result should not be None"
    assert gemini_result.success, f"Gemini extraction should succeed. Error: {gemini_result.error_message}"
    assert gemini_result.extracted_json, "Gemini should extract structured JSON"
    assert gemini_result.processing_time_ms > 0, "Processing time should be positive"

    # Check extracted fields
    extracted = gemini_result.extracted_json
    expected_fields = [
        "mittente",
        "destinatario",
        "indirizzo_destinazione_completo",
        "data_documento",
        "data_trasporto",
        "numero_documento",
        "numero_ordine",
        "codice_cliente",
    ]

    for field in expected_fields:
        assert field in extracted, f"Field '{field}' should be in extracted JSON"

    print(f"\n✓ Gemini extraction successful")
    print(f"  - Processing time: {gemini_result.processing_time_ms}ms")
    print(f"  - Extracted fields: {list(extracted.keys())}")
    print(f"  - Sample data:")
    print(f"    mittente: {extracted.get('mittente')}")
    print(f"    destinatario: {extracted.get('destinatario')}")
    print(f"    numero_documento: {extracted.get('numero_documento')}")

    return gemini_result


@pytest.mark.asyncio
async def test_full_pipeline_azure_gemini():
    """Test complete Azure → Gemini pipeline."""
    if not SAMPLE_PDF_PATH.exists():
        pytest.skip(f"Sample PDF not found: {SAMPLE_PDF_PATH}")

    pdf_bytes = SAMPLE_PDF_PATH.read_bytes()

    # Initialize extractors
    azure = AzureOCRExtractor(timeout=60, max_retries=3)
    gemini = GeminiExtractor(max_retries=2, timeout=60)

    # Step 1: Azure OCR
    print("\n[1/2] Running Azure OCR...")
    azure_result = await azure.extract(pdf_bytes, SAMPLE_PDF_PATH.name)
    assert azure_result.success, f"Azure failed: {azure_result.error_message}"

    # Step 2: Gemini extraction
    print("[2/2] Running Gemini extraction...")
    gemini_result = await gemini.extract(azure_result.raw_text, SAMPLE_PDF_PATH.name)
    assert gemini_result.success, f"Gemini failed: {gemini_result.error_message}"

    # Validate pipeline output
    print(f"\n✓ Full pipeline successful")
    print(f"  - Azure OCR time: {azure_result.processing_time_ms}ms")
    print(f"  - Gemini time: {gemini_result.processing_time_ms}ms")
    print(f"  - Total time: {azure_result.processing_time_ms + gemini_result.processing_time_ms}ms")
    print(f"\n  Extracted DDT data:")

    for field, value in gemini_result.extracted_json.items():
        print(f"    {field}: {value}")


if __name__ == "__main__":
    # Run tests directly for debugging
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    print("Testing Azure OCR and Gemini extractors...\n")

    # Run all tests
    asyncio.run(test_azure_ocr_extraction())
    print("\n" + "="*60)
    asyncio.run(test_gemini_extraction_from_azure())
    print("\n" + "="*60)
    asyncio.run(test_full_pipeline_azure_gemini())

    print("\n✓ All extractor tests passed!")
