"""Processing pipeline for DDT dataset generation.

This module orchestrates the complete processing flow:
1. Fetch PDF from Supabase Storage
2. Run Datalab extraction (OCR + structured data)
3. Run Azure OCR extraction
4. Run Gemini extraction on Azure OCR
5. Compare Datalab vs Gemini results
6. Calculate match score and determine validation status
7. Update database with results

Concurrency: Max 2 PDFs processed in parallel
"""

import asyncio
import logging
import time
from typing import Optional, List
from dataclasses import dataclass

from src.config import settings
from src.database import (
    SampleRepository,
    StatsRepository,
    SampleStatus,
    ValidationSource,
    get_pdf_bytes,
)
from src.extractors import (
    DatalabExtractor,
    AzureOCRExtractor,
    GeminiExtractor,
)
from src.processing.comparison import calculate_match_score

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result from processing a single PDF."""

    sample_id: str
    success: bool
    status: SampleStatus
    match_score: Optional[float] = None
    discrepancies: Optional[List[str]] = None
    error_message: Optional[str] = None
    processing_time_ms: int = 0


@dataclass
class ProcessingSummary:
    """Summary of batch processing."""

    total_processed: int
    successful: int
    failed: int
    auto_validated: int
    needs_review: int
    total_time_ms: int


class ProcessingPipeline:
    """Main processing pipeline for DDT extraction and validation.

    This class orchestrates the complete workflow:
    - Parallel execution of extractors
    - Cross-validation between Datalab and Gemini
    - Auto-validation based on match score threshold
    - Database updates and progress tracking

    Configuration:
        - Max parallel PDFs: From settings.MAX_PARALLEL_PDFS (default: 2)
        - Auto-validation threshold: 0.95 (95% match)

    Example:
        >>> pipeline = ProcessingPipeline()
        >>> result = await pipeline.process_single(sample_id="abc-123")
        >>> summary = await pipeline.process_all_pending()
    """

    def __init__(self):
        """Initialize processing pipeline with extractors and repositories."""
        self.sample_repo = SampleRepository()
        self.stats_repo = StatsRepository()

        # Initialize extractors
        self.datalab = DatalabExtractor(
            poll_interval=3,
            max_polls=100,
        )
        self.azure_ocr = AzureOCRExtractor(
            timeout=60,
            max_retries=3,
        )
        self.gemini = GeminiExtractor(
            max_retries=2,
            timeout=60,
        )

        # Concurrency control
        self.max_parallel = settings.MAX_PARALLEL_PDFS
        self.semaphore = asyncio.Semaphore(self.max_parallel)

        # Validation threshold
        self.auto_validation_threshold = 0.95

        logger.info(
            f"Initialized ProcessingPipeline: "
            f"max_parallel={self.max_parallel}, "
            f"auto_validation_threshold={self.auto_validation_threshold}"
        )

    async def process_single(self, sample_id: str) -> ProcessingResult:
        """Process a single PDF sample through the complete pipeline.

        Steps:
        1. Fetch PDF from storage
        2. Run Datalab extraction
        3. Run Azure OCR (if available)
        4. Run Gemini extraction on Azure OCR (if available)
        5. Calculate match score
        6. Determine validation status
        7. Update database

        Args:
            sample_id: UUID of the sample to process

        Returns:
            ProcessingResult with status and metrics
        """
        start_time = time.time()

        async with self.semaphore:  # Concurrency control
            try:
                logger.info(f"Starting processing for sample {sample_id}")

                # Step 1: Get sample from database
                sample = self.sample_repo.get_sample(sample_id)
                if not sample:
                    raise ValueError(f"Sample {sample_id} not found")

                # Update status to processing
                self.sample_repo.update_sample(
                    sample_id,
                    status=SampleStatus.PROCESSING
                )

                # Step 2: Fetch PDF from storage
                logger.info(f"Fetching PDF for {sample.filename}")
                pdf_bytes = get_pdf_bytes(sample.pdf_storage_path)

                # Step 3: Run Datalab extraction
                logger.info(f"Running Datalab extraction for {sample.filename}")
                datalab_result = await self.datalab.extract(pdf_bytes, sample.filename)

                # Step 4: Run Azure OCR extraction (parallel with Datalab would be ideal, but sequential is fine)
                azure_result = None
                gemini_result = None

                try:
                    logger.info(f"Running Azure OCR for {sample.filename}")
                    azure_result = await self.azure_ocr.extract(pdf_bytes, sample.filename)

                    # Step 5: Run Gemini extraction on Azure OCR text
                    if azure_result and azure_result.success:
                        logger.info(f"Running Gemini extraction for {sample.filename}")
                        gemini_result = await self.gemini.extract(
                            azure_result.raw_text,
                            sample.filename
                        )
                except Exception as e:
                    logger.warning(f"Azure/Gemini pipeline failed for {sample.filename}: {e}")
                    # Continue with Datalab-only processing

                # Step 6: Calculate match score and determine status
                match_score = None
                discrepancies = []
                validated_output = {}
                validation_source = ValidationSource.DATALAB
                status = SampleStatus.AUTO_VALIDATED

                if (datalab_result.success and
                    gemini_result and gemini_result.success and
                    datalab_result.extracted_json and gemini_result.extracted_json):
                    # Both extractors succeeded - compare results
                    match_score, discrepancies = calculate_match_score(
                        datalab_result.extracted_json,
                        gemini_result.extracted_json
                    )

                    if match_score >= self.auto_validation_threshold:
                        # Auto-validate with Datalab output (default)
                        status = SampleStatus.AUTO_VALIDATED
                        validated_output = datalab_result.extracted_json
                        validation_source = ValidationSource.DATALAB
                    else:
                        # Needs manual review
                        status = SampleStatus.NEEDS_REVIEW
                        validated_output = {}  # Will be set during manual review

                elif datalab_result.success and datalab_result.extracted_json:
                    # Only Datalab succeeded - auto-validate without comparison
                    logger.warning(f"Only Datalab succeeded for {sample.filename}, auto-validating without cross-validation")
                    status = SampleStatus.AUTO_VALIDATED
                    validated_output = datalab_result.extracted_json
                    validation_source = ValidationSource.DATALAB
                    match_score = None  # No comparison available

                else:
                    # Datalab failed - mark as error
                    status = SampleStatus.ERROR
                    validated_output = {}

                # Step 7: Update database
                processing_time_ms = int((time.time() - start_time) * 1000)

                update_data = {
                    "status": status,
                    "datalab_raw_ocr": datalab_result.raw_ocr if datalab_result.success else None,
                    "datalab_json": datalab_result.extracted_json if datalab_result.success else None,
                    "datalab_processing_time_ms": datalab_result.processing_time_ms,
                    "datalab_error": datalab_result.error_message,
                }

                if azure_result:
                    update_data.update({
                        "azure_raw_ocr": azure_result.raw_text if azure_result.success else None,
                        "azure_processing_time_ms": azure_result.processing_time_ms,
                        "azure_error": azure_result.error_message,
                    })

                if gemini_result:
                    update_data.update({
                        "gemini_json": gemini_result.extracted_json if gemini_result.success else None,
                        "gemini_processing_time_ms": gemini_result.processing_time_ms,
                        "gemini_error": gemini_result.error_message,
                    })

                if match_score is not None:
                    update_data.update({
                        "match_score": match_score,
                        "discrepancies": discrepancies,
                    })

                if validated_output:
                    update_data.update({
                        "validated_output": validated_output,
                        "validation_source": validation_source,
                    })

                self.sample_repo.update_sample(sample_id, **update_data)

                # Update stats
                if status == SampleStatus.AUTO_VALIDATED:
                    self.stats_repo.increment_counters(auto_validated=1, processed=1)
                elif status == SampleStatus.NEEDS_REVIEW:
                    self.stats_repo.increment_counters(needs_review=1, processed=1)
                elif status == SampleStatus.ERROR:
                    self.stats_repo.increment_counters(errors=1, processed=1)

                logger.info(
                    f"Completed processing for {sample.filename}: "
                    f"status={status.value}, match_score={match_score}, "
                    f"time={processing_time_ms}ms"
                )

                return ProcessingResult(
                    sample_id=sample_id,
                    success=True,
                    status=status,
                    match_score=match_score,
                    discrepancies=discrepancies,
                    processing_time_ms=processing_time_ms,
                )

            except Exception as e:
                # Handle errors - mark sample as error
                processing_time_ms = int((time.time() - start_time) * 1000)
                error_msg = str(e)

                logger.error(f"Processing failed for sample {sample_id}: {e}", exc_info=True)

                # Update sample status to error
                try:
                    self.sample_repo.update_sample(
                        sample_id,
                        status=SampleStatus.ERROR,
                        datalab_error=error_msg,
                    )
                    self.stats_repo.increment_counters(errors=1, processed=1)
                except Exception as update_error:
                    logger.error(f"Failed to update sample status: {update_error}")

                return ProcessingResult(
                    sample_id=sample_id,
                    success=False,
                    status=SampleStatus.ERROR,
                    error_message=error_msg,
                    processing_time_ms=processing_time_ms,
                )

    async def process_all_pending(self) -> ProcessingSummary:
        """Process all pending samples in the database.

        Processes samples in parallel (max MAX_PARALLEL_PDFS at a time).
        Updates processing stats after each sample.

        Returns:
            ProcessingSummary with batch statistics
        """
        start_time = time.time()

        logger.info("Starting batch processing of all pending samples")

        # Set processing flag
        self.stats_repo.set_processing_flag(True)

        try:
            # Get all pending samples
            pending_samples = self.sample_repo.get_samples(
                status=SampleStatus.PENDING,
                limit=1000  # Process up to 1000 at a time
            )

            total_count = len(pending_samples)
            logger.info(f"Found {total_count} pending samples to process")

            if total_count == 0:
                return ProcessingSummary(
                    total_processed=0,
                    successful=0,
                    failed=0,
                    auto_validated=0,
                    needs_review=0,
                    total_time_ms=0,
                )

            # Process all samples with concurrency control
            tasks = [
                self.process_single(sample.id)
                for sample in pending_samples
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Analyze results
            successful = 0
            failed = 0
            auto_validated = 0
            needs_review = 0

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed with exception: {result}")
                    failed += 1
                    continue

                if result.success:
                    successful += 1
                    if result.status == SampleStatus.AUTO_VALIDATED:
                        auto_validated += 1
                    elif result.status == SampleStatus.NEEDS_REVIEW:
                        needs_review += 1
                else:
                    failed += 1

            total_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Batch processing completed: "
                f"total={total_count}, successful={successful}, failed={failed}, "
                f"auto_validated={auto_validated}, needs_review={needs_review}, "
                f"time={total_time_ms}ms"
            )

            return ProcessingSummary(
                total_processed=total_count,
                successful=successful,
                failed=failed,
                auto_validated=auto_validated,
                needs_review=needs_review,
                total_time_ms=total_time_ms,
            )

        finally:
            # Clear processing flag
            self.stats_repo.set_processing_flag(False)
