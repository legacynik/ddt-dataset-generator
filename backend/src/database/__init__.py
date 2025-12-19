"""Database package for DDT Dataset Generator.

This package provides database clients, models, repositories, and storage utilities
for interacting with Supabase.
"""

from .client import get_client, get_storage
from .models import (
    DatasetSample,
    ProcessingStats,
    SampleStatus,
    ValidationSource,
    DatasetSplit,
    # Playground models
    Extractor,
    ExtractorType,
    ExtractionRun,
    ExtractionResult,
    FieldAccuracy,
    RunStatus,
)
from .repository import SampleRepository, StatsRepository
from .storage import upload_pdf, get_pdf_url, delete_pdf, get_pdf_bytes

__all__ = [
    # Client functions
    "get_client",
    "get_storage",
    # Models
    "DatasetSample",
    "ProcessingStats",
    "SampleStatus",
    "ValidationSource",
    "DatasetSplit",
    # Playground models
    "Extractor",
    "ExtractorType",
    "ExtractionRun",
    "ExtractionResult",
    "FieldAccuracy",
    "RunStatus",
    # Repositories
    "SampleRepository",
    "StatsRepository",
    # Storage functions
    "upload_pdf",
    "get_pdf_url",
    "delete_pdf",
    "get_pdf_bytes",
]
