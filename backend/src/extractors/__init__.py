"""Extractors package for DDT data extraction.

This package contains extractors for processing PDF documents and extracting
structured DDT data using various AI services:
- Datalab: OCR + Structured extraction
- Azure Document Intelligence: OCR only
- Gemini: Structured extraction from OCR text
"""

from src.extractors.schemas import (
    DDTOutput,
    DDT_EXTRACTION_SCHEMA,
    DatalabResult,
    AzureOCRResult,
    GeminiResult,
)
from src.extractors.datalab import DatalabExtractor, DatalabError, DatalabTimeoutError
from src.extractors.azure_ocr import AzureOCRExtractor, AzureOCRError, AzureRateLimitError
from src.extractors.gemini import GeminiExtractor, GeminiError, GeminiJSONError

__all__ = [
    "DDTOutput",
    "DDT_EXTRACTION_SCHEMA",
    "DatalabResult",
    "AzureOCRResult",
    "GeminiResult",
    "DatalabExtractor",
    "DatalabError",
    "DatalabTimeoutError",
    "AzureOCRExtractor",
    "AzureOCRError",
    "AzureRateLimitError",
    "GeminiExtractor",
    "GeminiError",
    "GeminiJSONError",
]
