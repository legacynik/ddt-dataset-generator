"""FastAPI routes for DDT Dataset Generator API.

This module implements all API endpoints for:
- PDF upload
- Batch processing
- Status monitoring
- Sample retrieval and validation
- Dataset export
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse

from .schemas import (
    UploadResponse,
    ProcessRequest,
    ProcessResponse,
    StatusResponse,
    SampleListResponse,
    SampleListItem,
    SampleDetailResponse,
    ValidationRequest,
    ValidationResponse,
    ExportRequest,
    ExportResponse,
    PreviousResultsResponse,
)
from src.database import (
    SampleRepository,
    StatsRepository,
    SampleStatus,
    upload_pdf,
    get_pdf_url,
)
from src.processing.pipeline import ProcessingPipeline
from src.processing.alpaca_formatter import export_dataset

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["api"])

# Global flag to track if processing is running
_is_processing = False


# ===== Helper Functions =====

async def _run_batch_processing(sample_ids: Optional[list[str]] = None):
    """Background task to run batch processing."""
    global _is_processing

    try:
        _is_processing = True
        logger.info("Starting batch processing in background")

        pipeline = ProcessingPipeline()

        if sample_ids:
            # Process specific samples
            logger.info(f"Processing {len(sample_ids)} specific samples")
            for sample_id in sample_ids:
                try:
                    await pipeline.process_single(sample_id)
                except Exception as e:
                    logger.error(f"Error processing sample {sample_id}: {e}")
        else:
            # Process all pending samples
            summary = await pipeline.process_all_pending()
            logger.info(
                f"Batch processing completed: {summary.total_processed} processed, "
                f"{summary.auto_validated} auto-validated, "
                f"{summary.needs_review} needs review, "
                f"{summary.errors} errors"
            )

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
    finally:
        _is_processing = False
        logger.info("Batch processing finished")


def _get_status_counts() -> dict:
    """Get current status counts from database."""
    repo = SampleRepository()

    # Count samples by status
    total = len(repo.get_samples(limit=10000))
    auto_validated = len(repo.get_samples(status=SampleStatus.AUTO_VALIDATED, limit=10000))
    needs_review = len(repo.get_samples(status=SampleStatus.NEEDS_REVIEW, limit=10000))
    manually_validated = len(repo.get_samples(status=SampleStatus.MANUALLY_VALIDATED, limit=10000))
    errors = len(repo.get_samples(status=SampleStatus.ERROR, limit=10000))
    pending = len(repo.get_samples(status=SampleStatus.PENDING, limit=10000))
    processing = len(repo.get_samples(status=SampleStatus.PROCESSING, limit=10000))

    processed = total - pending - processing

    progress_percent = (processed / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "processed": processed,
        "auto_validated": auto_validated,
        "needs_review": needs_review,
        "manually_validated": manually_validated,
        "errors": errors,
        "pending": pending,
        "progress_percent": round(progress_percent, 1),
    }


# ===== API Endpoints =====

@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_pdf_endpoint(
    file: UploadFile = File(..., description="PDF file to upload")
) -> UploadResponse:
    """Upload a PDF file for processing.

    The file is stored in Supabase Storage and a database record is created
    with status 'pending'.

    Args:
        file: PDF file (multipart/form-data)

    Returns:
        UploadResponse with sample ID, filename, status, and PDF URL

    Raises:
        HTTPException 400: If file is not a PDF or is too large
        HTTPException 500: If upload fails
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF (*.pdf)"
        )

    # Read file content
    try:
        pdf_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read file: {str(e)}"
        )

    # Check file size (max 50MB)
    max_size = 50 * 1024 * 1024  # 50MB
    if len(pdf_bytes) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(pdf_bytes)} bytes). Max size: {max_size} bytes"
        )

    logger.info(f"Uploading PDF: {file.filename} ({len(pdf_bytes)} bytes)")

    # Upload to Supabase Storage
    try:
        storage_path = upload_pdf(pdf_bytes, file.filename)
    except Exception as e:
        logger.error(f"Failed to upload PDF to storage: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file to storage: {str(e)}"
        )

    # Create database record
    try:
        repo = SampleRepository()
        sample = repo.create_sample(
            filename=file.filename,
            pdf_path=storage_path,
            file_size=len(pdf_bytes)
        )
    except Exception as e:
        logger.error(f"Failed to create database record: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create database record: {str(e)}"
        )

    # Generate signed URL
    try:
        pdf_url = get_pdf_url(storage_path, expires_in=3600)
    except Exception as e:
        logger.warning(f"Failed to generate PDF URL: {e}")
        pdf_url = None

    logger.info(f"PDF uploaded successfully: {sample.id} - {file.filename}")

    return UploadResponse(
        id=str(sample.id),
        filename=sample.filename,
        status=sample.status,
        pdf_url=pdf_url
    )


@router.post("/process", response_model=ProcessResponse)
async def start_processing(
    background_tasks: BackgroundTasks,
    request: ProcessRequest = ProcessRequest(sample_ids=None)
) -> ProcessResponse:
    """Start batch processing of pending samples.

    Processes all samples with status 'pending' through the full extraction pipeline
    (Datalab + Azure + Gemini) and calculates match scores.

    Processing runs in the background. Use GET /api/status to monitor progress.

    Args:
        background_tasks: FastAPI background tasks
        request: Optional list of specific sample IDs to process

    Returns:
        ProcessResponse with message and pending count

    Raises:
        HTTPException 409: If processing is already running
    """
    global _is_processing

    if _is_processing:
        raise HTTPException(
            status_code=409,
            detail="Processing is already running. Please wait for it to complete."
        )

    # Get pending samples count
    repo = SampleRepository()

    if request.sample_ids:
        pending_count = len(request.sample_ids)
        logger.info(f"Queueing {pending_count} specific samples for processing")
    else:
        pending_samples = repo.get_samples(status=SampleStatus.PENDING, limit=10000)
        pending_count = len(pending_samples)
        logger.info(f"Queueing {pending_count} pending samples for processing")

    if pending_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No pending samples to process"
        )

    # Start background processing
    background_tasks.add_task(_run_batch_processing, request.sample_ids)

    return ProcessResponse(
        message="Processing started",
        pending_count=pending_count
    )


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Get current processing status.

    Returns real-time statistics about sample processing progress.

    Returns:
        StatusResponse with processing status and counts by status
    """
    global _is_processing

    counts = _get_status_counts()

    return StatusResponse(
        is_processing=_is_processing,
        total=counts["total"],
        processed=counts["processed"],
        auto_validated=counts["auto_validated"],
        needs_review=counts["needs_review"],
        manually_validated=counts["manually_validated"],
        errors=counts["errors"],
        pending=counts["pending"],
        progress_percent=counts["progress_percent"]
    )


@router.get("/samples", response_model=SampleListResponse)
async def list_samples(
    status: Optional[SampleStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset")
) -> SampleListResponse:
    """List samples with optional filtering and pagination.

    Args:
        status: Filter by sample status (optional)
        limit: Maximum number of results (1-200, default 50)
        offset: Pagination offset (default 0)

    Returns:
        SampleListResponse with list of samples and pagination info
    """
    repo = SampleRepository()

    # Get samples
    samples = repo.get_samples(status=status, limit=limit, offset=offset)

    # Get total count (for pagination)
    total = len(repo.get_samples(status=status, limit=10000))

    # Convert to response models
    sample_items = []
    for sample in samples:
        sample_items.append(
            SampleListItem(
                id=str(sample.id),
                filename=sample.filename,
                status=sample.status,
                match_score=sample.match_score,
                discrepancies=sample.discrepancies,
                created_at=sample.created_at,
                updated_at=sample.updated_at
            )
        )

    return SampleListResponse(
        samples=sample_items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/samples/{sample_id}", response_model=SampleDetailResponse)
async def get_sample_detail(sample_id: str) -> SampleDetailResponse:
    """Get detailed information about a specific sample.

    Includes all extraction outputs, OCR text, and validation metadata.
    Useful for the review interface.

    Args:
        sample_id: Sample UUID

    Returns:
        SampleDetailResponse with complete sample data

    Raises:
        HTTPException 404: If sample not found
    """
    repo = SampleRepository()

    # Get sample
    sample = repo.get_sample(sample_id)

    if not sample:
        raise HTTPException(
            status_code=404,
            detail=f"Sample not found: {sample_id}"
        )

    # Generate signed PDF URL
    pdf_url = None
    if sample.pdf_storage_path:
        try:
            pdf_url = get_pdf_url(sample.pdf_storage_path, expires_in=3600)
        except Exception as e:
            logger.warning(f"Failed to generate PDF URL for {sample_id}: {e}")

    return SampleDetailResponse(
        id=str(sample.id),
        filename=sample.filename,
        pdf_url=pdf_url,
        storage_path=sample.pdf_storage_path,
        status=sample.status,
        match_score=sample.match_score,
        discrepancies=sample.discrepancies,
        datalab_json=sample.datalab_json,
        gemini_json=sample.gemini_json,
        validated_output=sample.validated_output,
        datalab_raw_ocr=sample.datalab_raw_ocr,
        azure_raw_ocr=sample.azure_raw_ocr,
        validation_source=sample.validation_source,
        validator_notes=sample.validator_notes,
        created_at=sample.created_at,
        updated_at=sample.updated_at
    )


@router.patch("/samples/{sample_id}", response_model=ValidationResponse)
async def validate_sample(
    sample_id: str,
    request: ValidationRequest
) -> ValidationResponse:
    """Manually validate or correct a sample.

    Allows reviewers to:
    - Accept Datalab or Gemini output as validated
    - Manually correct extraction errors
    - Reject samples
    - Add validation notes

    Args:
        sample_id: Sample UUID
        request: Validation data (status, validated_output, source, notes)

    Returns:
        ValidationResponse with updated status

    Raises:
        HTTPException 404: If sample not found
        HTTPException 400: If validation data is invalid
    """
    repo = SampleRepository()

    # Get sample
    sample = repo.get_sample(sample_id)

    if not sample:
        raise HTTPException(
            status_code=404,
            detail=f"Sample not found: {sample_id}"
        )

    # Prepare update fields
    update_fields = {}

    if request.status:
        update_fields["status"] = request.status

    if request.validated_output:
        update_fields["validated_output"] = request.validated_output

    if request.validation_source:
        update_fields["validation_source"] = request.validation_source

    if request.validator_notes is not None:
        update_fields["validator_notes"] = request.validator_notes

    if not update_fields:
        raise HTTPException(
            status_code=400,
            detail="No fields to update"
        )

    logger.info(f"Validating sample {sample_id}: {update_fields.keys()}")

    # Update sample
    try:
        updated_sample = repo.update_sample(sample_id, **update_fields)
    except Exception as e:
        logger.error(f"Failed to update sample {sample_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update sample: {str(e)}"
        )

    return ValidationResponse(
        id=updated_sample.id,
        status=updated_sample.status,
        updated_at=updated_sample.updated_at
    )


@router.post("/export", response_model=ExportResponse)
async def export_dataset_endpoint(
    request: ExportRequest = ExportRequest()
) -> ExportResponse:
    """Export validated samples to Alpaca JSONL format.

    Generates training and validation datasets from auto-validated and
    manually-validated samples.

    Files are saved to the output directory and download URLs are returned.

    Args:
        request: Export configuration (OCR source, validation split ratio)

    Returns:
        ExportResponse with export statistics and download URLs

    Raises:
        HTTPException 400: If no validated samples available
        HTTPException 500: If export fails
    """
    logger.info(
        f"Starting dataset export: ocr_source={request.ocr_source}, "
        f"validation_split={request.validation_split}"
    )

    # Create output directory
    output_dir = Path(__file__).parent.parent.parent / "output" / "exports"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = output_dir / f"export_{timestamp}"
    export_dir.mkdir(parents=True, exist_ok=True)

    # Run export
    try:
        stats = export_dataset(
            output_dir=export_dir,
            ocr_source=request.ocr_source,
            validation_ratio=request.validation_split
        )
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )

    if stats.total_samples == 0:
        raise HTTPException(
            status_code=400,
            detail="No validated samples available for export"
        )

    # Generate download URLs (file paths for now, could be signed URLs in production)
    download_urls = {
        "training": str(export_dir / "train.jsonl"),
        "validation": str(export_dir / "validation.jsonl"),
        "report": str(export_dir / "quality_report.json")
    }

    logger.info(
        f"Export completed: {stats.total_samples} samples "
        f"({stats.train_samples} train, {stats.validation_samples} val)"
    )

    return ExportResponse(
        total_samples=stats.total_samples,
        training_samples=stats.train_samples,
        validation_samples=stats.validation_samples,
        ocr_source=stats.ocr_source,
        download_urls=download_urls,
        quality_report={
            "field_coverage": stats.field_coverage,
            "avg_ocr_length": stats.avg_ocr_length,
            "avg_output_length": stats.avg_output_length,
            "quality_score": sum(stats.field_coverage.values()) / len(stats.field_coverage)
            if stats.field_coverage else 0.0
        }
    )


@router.get("/previous-results", response_model=PreviousResultsResponse)
async def get_previous_results() -> PreviousResultsResponse:
    """Get statistics from the previous processing report.

    Reads the DDT_PROCESSING_REPORT.md file and extracts key statistics
    to display in the dashboard as historical results.

    Returns:
        PreviousResultsResponse with aggregated statistics

    Raises:
        HTTPException 404: If report file not found
    """
    import re
    from pathlib import Path

    # Look for report in parent directory (project root)
    report_path = Path(__file__).parent.parent.parent.parent / "DDT_PROCESSING_REPORT.md"

    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Previous processing report not found"
        )

    try:
        content = report_path.read_text()

        # Extract statistics using regex
        generated_match = re.search(r'\*\*Generated:\*\* (.+)', content)
        total_match = re.search(r'\*\*Total PDFs Processed:\*\* (\d+)', content)
        datalab_match = re.search(r'- \*\*Datalab Success:\*\* (\d+)/(\d+)', content)
        azure_match = re.search(r'- \*\*Azure Success:\*\* (\d+)/(\d+)', content)
        gemini_match = re.search(r'- \*\*Gemini Success:\*\* (\d+)/(\d+)', content)
        auto_validated_match = re.search(r'- \*\*Auto-Validated:\*\* (\d+)/(\d+)', content)
        needs_review_match = re.search(r'- \*\*Needs Review:\*\* (\d+)/(\d+)', content)
        avg_time_match = re.search(r'- \*\*Total \(per PDF\):\*\* ([\d.]+)s', content)

        # Calculate statistics
        total_pdfs = int(total_match.group(1)) if total_match else 0

        datalab_success = int(datalab_match.group(1)) if datalab_match else 0
        datalab_total = int(datalab_match.group(2)) if datalab_match else 1

        azure_success = int(azure_match.group(1)) if azure_match else 0
        azure_total = int(azure_match.group(2)) if azure_match else 1

        gemini_success = int(gemini_match.group(1)) if gemini_match else 0
        gemini_total = int(gemini_match.group(2)) if gemini_match else 1

        auto_validated = int(auto_validated_match.group(1)) if auto_validated_match else 0
        needs_review = int(needs_review_match.group(1)) if needs_review_match else 0

        # Error count = total - auto_validated - needs_review
        error_count = total_pdfs - auto_validated - needs_review

        return PreviousResultsResponse(
            total_pdfs=total_pdfs,
            generated_at=generated_match.group(1) if generated_match else "Unknown",
            datalab_success_rate=datalab_success / datalab_total if datalab_total > 0 else 0.0,
            azure_success_rate=azure_success / azure_total if azure_total > 0 else 0.0,
            gemini_success_rate=gemini_success / gemini_total if gemini_total > 0 else 0.0,
            auto_validated_count=auto_validated,
            needs_review_count=needs_review,
            error_count=error_count,
            avg_processing_time=float(avg_time_match.group(1)) if avg_time_match else 0.0
        )

    except Exception as e:
        logger.error(f"Failed to parse previous results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse report: {str(e)}"
        )
