"""Pydantic schemas for API request/response models."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from src.database.models import SampleStatus, ValidationSource


# ===== Upload =====

class UploadResponse(BaseModel):
    """Response from POST /api/upload."""

    id: str = Field(..., description="Sample UUID")
    filename: str = Field(..., description="Original PDF filename")
    status: SampleStatus = Field(..., description="Initial status (pending)")
    pdf_url: Optional[str] = Field(None, description="Signed URL for PDF download")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "ddt_001.pdf",
                "status": "pending",
                "pdf_url": "https://..."
            }
        }


# ===== Process =====

class ProcessRequest(BaseModel):
    """Request body for POST /api/process (optional)."""

    sample_ids: Optional[List[str]] = Field(
        None,
        description="Specific sample IDs to process (if None, process all pending)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sample_ids": None  # Process all pending
            }
        }


class ProcessResponse(BaseModel):
    """Response from POST /api/process."""

    message: str = Field(..., description="Success message")
    pending_count: int = Field(..., description="Number of samples queued for processing")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Processing started",
                "pending_count": 5
            }
        }


# ===== Status =====

class StatusResponse(BaseModel):
    """Response from GET /api/status."""

    is_processing: bool = Field(..., description="Whether processing is currently running")
    total: int = Field(..., description="Total samples in database")
    processed: int = Field(..., description="Number of processed samples (any non-pending status)")
    auto_validated: int = Field(..., description="Number of auto-validated samples")
    needs_review: int = Field(..., description="Number of samples needing review")
    manually_validated: int = Field(..., description="Number of manually validated samples")
    errors: int = Field(..., description="Number of samples with errors")
    pending: int = Field(..., description="Number of pending samples")
    progress_percent: float = Field(..., description="Processing progress percentage (0-100)")

    class Config:
        json_schema_extra = {
            "example": {
                "is_processing": True,
                "total": 5,
                "processed": 2,
                "auto_validated": 1,
                "needs_review": 1,
                "manually_validated": 0,
                "errors": 0,
                "pending": 3,
                "progress_percent": 40.0
            }
        }


# ===== Samples List =====

class SampleListItem(BaseModel):
    """Single sample in list response."""

    id: str = Field(..., description="Sample UUID")
    filename: str = Field(..., description="PDF filename")
    status: SampleStatus = Field(..., description="Current status")
    match_score: Optional[float] = Field(None, description="Match score (0.0-1.0)")
    discrepancies: Optional[List[str]] = Field(None, description="List of fields with discrepancies")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "ddt_001.pdf",
                "status": "needs_review",
                "match_score": 0.875,
                "discrepancies": ["numero_documento", "data_trasporto"],
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:05:00Z"
            }
        }


class SampleListResponse(BaseModel):
    """Response from GET /api/samples."""

    samples: List[SampleListItem] = Field(..., description="List of samples")
    total: int = Field(..., description="Total number of samples (for pagination)")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Pagination offset")

    class Config:
        json_schema_extra = {
            "example": {
                "samples": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "filename": "ddt_001.pdf",
                        "status": "needs_review",
                        "match_score": 0.875,
                        "discrepancies": ["numero_documento"],
                        "created_at": "2025-01-15T10:00:00Z",
                        "updated_at": "2025-01-15T10:05:00Z"
                    }
                ],
                "total": 30,
                "limit": 50,
                "offset": 0
            }
        }


# ===== Sample Detail =====

class SampleDetailResponse(BaseModel):
    """Response from GET /api/samples/{id}."""

    id: str = Field(..., description="Sample UUID")
    filename: str = Field(..., description="PDF filename")
    pdf_url: Optional[str] = Field(None, description="Signed URL for PDF download")
    storage_path: Optional[str] = Field(None, description="Storage path in bucket")
    status: SampleStatus = Field(..., description="Current status")
    match_score: Optional[float] = Field(None, description="Match score (0.0-1.0)")
    discrepancies: Optional[List[str]] = Field(None, description="Fields with discrepancies")

    # Extraction outputs
    datalab_json: Optional[Dict[str, Any]] = Field(None, description="Datalab structured output")
    gemini_json: Optional[Dict[str, Any]] = Field(None, description="Gemini structured output")
    validated_output: Optional[Dict[str, Any]] = Field(None, description="Final validated output")

    # Raw OCR text
    datalab_raw_ocr: Optional[str] = Field(None, description="Datalab raw OCR text")
    azure_raw_ocr: Optional[str] = Field(None, description="Azure raw OCR text")

    # Validation metadata
    validation_source: Optional[ValidationSource] = Field(None, description="Source of validated output")
    validator_notes: Optional[str] = Field(None, description="Manual validation notes")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "ddt_001.pdf",
                "pdf_url": "https://...",
                "storage_path": "pdfs/ddt_001.pdf",
                "status": "needs_review",
                "match_score": 0.875,
                "discrepancies": ["numero_documento"],
                "datalab_json": {"mittente": "LAVAZZA", "...": "..."},
                "gemini_json": {"mittente": "LAVAZZA", "...": "..."},
                "validated_output": None,
                "datalab_raw_ocr": "LAVAZZA S.p.A...",
                "azure_raw_ocr": "LAVAZZA S.p.A...",
                "validation_source": None,
                "validator_notes": None,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:05:00Z"
            }
        }


# ===== Validation =====

class ValidationRequest(BaseModel):
    """Request body for PATCH /api/samples/{id}."""

    status: Optional[SampleStatus] = Field(None, description="New status")
    validated_output: Optional[Dict[str, Any]] = Field(None, description="Manually corrected DDT fields")
    validation_source: Optional[ValidationSource] = Field(None, description="Source: datalab/gemini/manual")
    validator_notes: Optional[str] = Field(None, description="Notes from manual review")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "manually_validated",
                "validated_output": {
                    "mittente": "LAVAZZA",
                    "destinatario": "CONAD",
                    "indirizzo_destinazione_completo": "Via Roma 123, Milano",
                    "data_documento": "2025-01-15",
                    "data_trasporto": "2025-01-16",
                    "numero_documento": "DDT-001",
                    "numero_ordine": "ORD-123",
                    "codice_cliente": "CLI-456"
                },
                "validation_source": "gemini",
                "validator_notes": "Corretto numero documento"
            }
        }


class ValidationResponse(BaseModel):
    """Response from PATCH /api/samples/{id}."""

    id: str = Field(..., description="Sample UUID")
    status: SampleStatus = Field(..., description="Updated status")
    updated_at: datetime = Field(..., description="Update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "manually_validated",
                "updated_at": "2025-01-15T10:30:00Z"
            }
        }


# ===== Export =====

class ExportRequest(BaseModel):
    """Request body for POST /api/export."""

    ocr_source: str = Field(
        "azure",
        description="OCR source to use as input: 'azure' or 'datalab'"
    )
    validation_split: float = Field(
        0.07,
        description="Validation set ratio (default 0.07 = 7%)",
        ge=0.0,
        le=0.5
    )

    class Config:
        json_schema_extra = {
            "example": {
                "ocr_source": "azure",
                "validation_split": 0.07
            }
        }


class ExportResponse(BaseModel):
    """Response from POST /api/export."""

    total_samples: int = Field(..., description="Total samples exported")
    training_samples: int = Field(..., description="Number of training samples")
    validation_samples: int = Field(..., description="Number of validation samples")
    ocr_source: str = Field(..., description="OCR source used")
    download_urls: Dict[str, str] = Field(..., description="Download URLs for generated files")
    quality_report: Optional[Dict[str, Any]] = Field(None, description="Quality metrics")

    class Config:
        json_schema_extra = {
            "example": {
                "total_samples": 300,
                "training_samples": 280,
                "validation_samples": 20,
                "ocr_source": "azure",
                "download_urls": {
                    "training": "https://.../train.jsonl",
                    "validation": "https://.../validation.jsonl",
                    "report": "https://.../quality_report.json"
                },
                "quality_report": {
                    "field_coverage": {
                        "mittente": 1.0,
                        "destinatario": 1.0,
                        "numero_documento": 0.98
                    },
                    "quality_score": 0.95
                }
            }
        }


# ===== Previous Results =====

class PreviousResultsResponse(BaseModel):
    """Response from GET /api/previous-results."""

    total_pdfs: int = Field(..., description="Total PDFs processed")
    generated_at: str = Field(..., description="Report generation timestamp")
    datalab_success_rate: float = Field(..., description="Datalab success rate (0-1)")
    azure_success_rate: float = Field(..., description="Azure success rate (0-1)")
    gemini_success_rate: float = Field(..., description="Gemini success rate (0-1)")
    auto_validated_count: int = Field(..., description="Number of auto-validated samples")
    needs_review_count: int = Field(..., description="Number of samples needing review")
    error_count: int = Field(..., description="Number of errors")
    avg_processing_time: float = Field(..., description="Average processing time per PDF (seconds)")

    class Config:
        json_schema_extra = {
            "example": {
                "total_pdfs": 22,
                "generated_at": "2025-12-18 00:48:49",
                "datalab_success_rate": 1.0,
                "azure_success_rate": 1.0,
                "gemini_success_rate": 0.955,
                "auto_validated_count": 6,
                "needs_review_count": 15,
                "error_count": 1,
                "avg_processing_time": 132.9
            }
        }
