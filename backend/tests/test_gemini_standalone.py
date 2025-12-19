"""Standalone test for Gemini extractor with mock OCR text.

Tests Gemini without requiring Azure, using sample OCR text.
"""

import pytest
import asyncio
from src.extractors import GeminiExtractor


# Sample OCR text (realistic Italian DDT content)
SAMPLE_OCR_TEXT = """
DOCUMENTO DI TRASPORTO N. DDT-2025-001
Data: 15/01/2025

MITTENTE:
BARILLA G. e R. FRATELLI S.p.A.
Via Mantova 166
43122 Parma (PR)
P.IVA: IT00857400345

DESTINATARIO:
CONAD SOC. COOP.
Via Michelino 59
40127 Bologna (BO)
P.IVA: IT00115740389

INDIRIZZO DI DESTINAZIONE:
CONAD SUPERSTORE
Via Roma 123
20100 Milano (MI)

DATA TRASPORTO: 16/01/2025
NUMERO ORDINE: ORD-5678
CODICE CLIENTE: CLI-1234

DESCRIZIONE MERCE:
- Pasta Barilla Spaghetti n.5 - 24 pz
- Pasta Barilla Penne Rigate - 12 pz

Totale Colli: 36
"""


@pytest.mark.asyncio
async def test_gemini_extraction_standalone():
    """Test Gemini extraction with sample OCR text."""
    # Initialize Gemini extractor
    gemini = GeminiExtractor(max_retries=2, timeout=60)

    # Extract structured data
    result = await gemini.extract(SAMPLE_OCR_TEXT, "sample_ddt.pdf")

    # Assertions
    assert result is not None, "Gemini result should not be None"
    assert result.success, f"Gemini extraction should succeed. Error: {result.error_message}"
    assert result.extracted_json, "Gemini should extract structured JSON"
    assert result.processing_time_ms > 0, "Processing time should be positive"

    # Check extracted fields
    extracted = result.extracted_json
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
    print(f"  - Processing time: {result.processing_time_ms}ms")
    print(f"  - Extracted fields: {list(extracted.keys())}")
    print(f"\n  Extracted DDT data:")

    for field, value in extracted.items():
        print(f"    {field}: {value}")

    # Validate specific expected values
    assert "BARILLA" in extracted.get("mittente", "").upper(), "Mittente should contain BARILLA"
    assert "CONAD" in extracted.get("destinatario", "").upper(), "Destinatario should contain CONAD"
    assert "DDT-2025-001" in extracted.get("numero_documento", ""), "Should extract document number"
    assert "2025-01-15" in extracted.get("data_documento", ""), "Should extract document date"

    return result


if __name__ == "__main__":
    # Run test directly
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    print("Testing Gemini extractor with sample OCR text...\n")
    asyncio.run(test_gemini_extraction_standalone())
    print("\n✓ Gemini test passed!")
