"""Pydantic models for database entities.

This module defines Pydantic models that map to the Supabase database schema,
providing type validation and serialization for all database operations.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SampleStatus(str, Enum):
    """Status of a dataset sample in the processing pipeline."""

    PENDING = "pending"
    PROCESSING = "processing"
    AUTO_VALIDATED = "auto_validated"
    NEEDS_REVIEW = "needs_review"
    MANUALLY_VALIDATED = "manually_validated"
    REJECTED = "rejected"
    ERROR = "error"


class ValidationSource(str, Enum):
    """Source of the validated output."""

    DATALAB = "datalab"
    GEMINI = "gemini"
    MANUAL = "manual"


class DatasetSplit(str, Enum):
    """Dataset split assignment for training or validation."""

    TRAIN = "train"
    VALIDATION = "validation"


class DatasetSample(BaseModel):
    """Model for dataset_samples table.

    This model represents a single DDT PDF sample with all its processing
    data from both Datalab and Azure+Gemini pipelines.

    Attributes:
        id: Unique identifier (UUID)
        created_at: Timestamp when the sample was created
        updated_at: Timestamp when the sample was last updated
        filename: Original PDF filename
        pdf_storage_path: Path to PDF in Supabase Storage
        file_size_bytes: Size of the PDF file in bytes
        datalab_raw_ocr: Raw OCR text from Datalab
        datalab_json: Structured data extracted by Datalab
        datalab_processing_time_ms: Processing time for Datalab pipeline
        datalab_error: Error message if Datalab processing failed
        azure_raw_ocr: Raw OCR text from Azure Document Intelligence
        azure_processing_time_ms: Processing time for Azure OCR
        azure_error: Error message if Azure processing failed
        gemini_json: Structured data extracted by Gemini
        gemini_processing_time_ms: Processing time for Gemini extraction
        gemini_error: Error message if Gemini processing failed
        match_score: Similarity score between Datalab and Gemini outputs (0.0-1.0)
        discrepancies: List of field names that don't match
        status: Current status in the processing pipeline
        validated_output: Final validated structured data (JSON)
        validation_source: Source of the validated output
        validator_notes: Notes from manual validation
        dataset_split: Whether this sample is for training or validation
    """

    # Primary key and timestamps
    id: UUID
    created_at: datetime
    updated_at: datetime

    # File info
    filename: str = Field(..., max_length=255)
    pdf_storage_path: str
    file_size_bytes: Optional[int] = None

    # Pipeline Datalab
    datalab_raw_ocr: Optional[str] = None
    datalab_json: Optional[dict[str, Any]] = None
    datalab_processing_time_ms: Optional[int] = None
    datalab_error: Optional[str] = None

    # Pipeline Azure + Gemini
    azure_raw_ocr: Optional[str] = None
    azure_processing_time_ms: Optional[int] = None
    azure_error: Optional[str] = None
    gemini_json: Optional[dict[str, Any]] = None
    gemini_processing_time_ms: Optional[int] = None
    gemini_error: Optional[str] = None

    # Comparison
    match_score: Optional[Decimal] = Field(None, ge=0, le=1)
    discrepancies: Optional[list[str]] = None

    # Validation
    status: SampleStatus = Field(default=SampleStatus.PENDING)
    validated_output: Optional[dict[str, Any]] = None
    validation_source: Optional[ValidationSource] = None
    validator_notes: Optional[str] = None

    # Dataset assignment
    dataset_split: Optional[DatasetSplit] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2025-12-17T10:00:00Z",
                "updated_at": "2025-12-17T10:30:00Z",
                "filename": "ddt_001.pdf",
                "pdf_storage_path": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
                "file_size_bytes": 524288,
                "status": "auto_validated",
                "match_score": 0.9875,
                "validated_output": {
                    "mittente": "LAVAZZA S.p.A.",
                    "destinatario": "CONAD SOC. COOP.",
                    "indirizzo_destinazione_completo": "Via Roma 123, 20100 Milano MI",
                    "data_documento": "2025-01-15",
                    "data_trasporto": "2025-01-16",
                    "numero_documento": "DDT-001234",
                    "numero_ordine": "ORD-5678",
                    "codice_cliente": "CLI-999",
                },
            }
        }
    }

    @field_validator("match_score", mode="before")
    @classmethod
    def convert_match_score(cls, v: Any) -> Optional[Decimal]:
        """Convert match score to Decimal if it's a float."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v


class ProcessingStats(BaseModel):
    """Model for processing_stats table.

    This is a single-row table that stores global processing statistics.
    It provides an overview of the entire dataset generation process.

    Attributes:
        id: Unique identifier (UUID)
        created_at: Timestamp when stats were created
        updated_at: Timestamp when stats were last updated
        total_samples: Total number of samples uploaded
        processed: Number of samples that have been processed
        auto_validated: Number of samples automatically validated
        needs_review: Number of samples requiring manual review
        manually_validated: Number of samples manually validated
        rejected: Number of rejected samples
        errors: Number of samples that failed with errors
        avg_match_score: Average match score across all samples
        total_processing_time_ms: Total processing time in milliseconds
        is_processing: Whether batch processing is currently running
    """

    # Primary key and timestamps
    id: UUID
    created_at: datetime
    updated_at: datetime

    # Counters
    total_samples: int = Field(default=0, ge=0)
    processed: int = Field(default=0, ge=0)
    auto_validated: int = Field(default=0, ge=0)
    needs_review: int = Field(default=0, ge=0)
    manually_validated: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)

    # Metrics
    avg_match_score: Optional[Decimal] = Field(None, ge=0, le=1)
    total_processing_time_ms: Optional[int] = Field(None, ge=0)

    # Processing flag
    is_processing: bool = Field(default=False)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "created_at": "2025-12-17T09:00:00Z",
                "updated_at": "2025-12-17T10:30:00Z",
                "total_samples": 300,
                "processed": 280,
                "auto_validated": 250,
                "needs_review": 25,
                "manually_validated": 5,
                "rejected": 0,
                "errors": 0,
                "avg_match_score": 0.943,
                "total_processing_time_ms": 4260000,
                "is_processing": False,
            }
        }
    }

    @field_validator("avg_match_score", mode="before")
    @classmethod
    def convert_avg_match_score(cls, v: Any) -> Optional[Decimal]:
        """Convert average match score to Decimal if it's a float."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

    @property
    def progress_percent(self) -> float:
        """Calculate processing progress as a percentage.

        Returns:
            Progress percentage (0-100). Returns 0 if no samples exist.
        """
        if self.total_samples == 0:
            return 0.0
        return round((self.processed / self.total_samples) * 100, 2)

    @property
    def validation_breakdown(self) -> dict[str, int]:
        """Get a breakdown of validation statuses.

        Returns:
            Dictionary with counts for each validation status.
        """
        return {
            "auto_validated": self.auto_validated,
            "needs_review": self.needs_review,
            "manually_validated": self.manually_validated,
            "rejected": self.rejected,
            "errors": self.errors,
        }
