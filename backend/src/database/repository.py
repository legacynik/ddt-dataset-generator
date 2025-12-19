"""Repository classes for database operations.

This module provides repository classes that abstract database operations
for dataset samples and processing statistics.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from .client import get_client
from .models import DatasetSample, ProcessingStats, SampleStatus

logger = logging.getLogger(__name__)


class SampleRepository:
    """Repository for managing dataset samples.

    This class provides methods for creating, reading, updating, and querying
    dataset samples in the Supabase database.
    """

    def __init__(self):
        """Initialize the repository with a Supabase client."""
        self.client = get_client()
        self.table_name = "dataset_samples"

    def create_sample(
        self, filename: str, pdf_path: str, file_size: int
    ) -> DatasetSample:
        """Create a new dataset sample.

        Args:
            filename: Original filename of the PDF
            pdf_path: Storage path where the PDF is stored
            file_size: Size of the PDF file in bytes

        Returns:
            DatasetSample: The created sample with generated ID and timestamps

        Raises:
            Exception: If database operation fails
        """
        logger.info(f"Creating new sample for file: {filename}")

        data = {
            "filename": filename,
            "pdf_storage_path": pdf_path,
            "file_size_bytes": file_size,
            "status": SampleStatus.PENDING.value,
        }

        response = self.client.table(self.table_name).insert(data).execute()

        if not response.data or len(response.data) == 0:
            raise Exception(f"Failed to create sample for {filename}")

        sample = DatasetSample(**response.data[0])
        logger.info(f"Sample created successfully with ID: {sample.id}")
        return sample

    def get_sample(self, sample_id: str | UUID) -> Optional[DatasetSample]:
        """Get a sample by ID.

        Args:
            sample_id: UUID of the sample (string or UUID object)

        Returns:
            DatasetSample if found, None otherwise
        """
        logger.debug(f"Fetching sample with ID: {sample_id}")

        response = (
            self.client.table(self.table_name)
            .select("*")
            .eq("id", str(sample_id))
            .execute()
        )

        if not response.data or len(response.data) == 0:
            logger.warning(f"Sample not found: {sample_id}")
            return None

        return DatasetSample(**response.data[0])

    def get_samples(
        self,
        status: Optional[SampleStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DatasetSample]:
        """Get a list of samples with optional filtering.

        Args:
            status: Filter by sample status (optional)
            limit: Maximum number of samples to return
            offset: Number of samples to skip for pagination

        Returns:
            List of DatasetSample objects
        """
        logger.debug(
            f"Fetching samples (status={status}, limit={limit}, offset={offset})"
        )

        query = self.client.table(self.table_name).select("*")

        if status is not None:
            query = query.eq("status", status.value)

        # Order by created_at descending (newest first)
        query = query.order("created_at", desc=True)

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        response = query.execute()

        samples = [DatasetSample(**item) for item in response.data]
        logger.debug(f"Retrieved {len(samples)} samples")
        return samples

    def update_sample(self, sample_id: str | UUID, **fields: Any) -> DatasetSample:
        """Update a sample with the given fields.

        Args:
            sample_id: UUID of the sample to update
            **fields: Field names and values to update

        Returns:
            Updated DatasetSample

        Raises:
            Exception: If sample not found or update fails

        Example:
            >>> repo = SampleRepository()
            >>> sample = repo.update_sample(
            ...     sample_id="123e4567-e89b-12d3-a456-426614174000",
            ...     status=SampleStatus.PROCESSING,
            ...     datalab_raw_ocr="Sample OCR text..."
            ... )
        """
        logger.info(f"Updating sample {sample_id} with fields: {list(fields.keys())}")

        # Convert enum values to strings
        update_data = {}
        for key, value in fields.items():
            if hasattr(value, "value"):  # Enum
                update_data[key] = value.value
            else:
                update_data[key] = value

        response = (
            self.client.table(self.table_name)
            .update(update_data)
            .eq("id", str(sample_id))
            .execute()
        )

        if not response.data or len(response.data) == 0:
            raise Exception(f"Failed to update sample {sample_id}")

        updated_sample = DatasetSample(**response.data[0])
        logger.info(f"Sample {sample_id} updated successfully")
        return updated_sample

    def count_by_status(self) -> dict[str, int]:
        """Count samples grouped by status.

        Returns:
            Dictionary mapping status names to counts

        Example:
            >>> repo = SampleRepository()
            >>> counts = repo.count_by_status()
            >>> print(counts)
            {"pending": 5, "processing": 2, "auto_validated": 10, ...}
        """
        logger.debug("Counting samples by status")

        # Get all samples (we'll count in memory for simplicity)
        # For large datasets, consider using Supabase aggregation functions
        response = self.client.table(self.table_name).select("status").execute()

        counts: dict[str, int] = {status.value: 0 for status in SampleStatus}

        for item in response.data:
            status = item.get("status")
            if status:
                counts[status] = counts.get(status, 0) + 1

        logger.debug(f"Status counts: {counts}")
        return counts

    def get_samples_by_ids(self, sample_ids: list[str | UUID]) -> list[DatasetSample]:
        """Get multiple samples by their IDs.

        Args:
            sample_ids: List of sample UUIDs

        Returns:
            List of DatasetSample objects
        """
        if not sample_ids:
            return []

        logger.debug(f"Fetching {len(sample_ids)} samples by IDs")

        # Convert UUIDs to strings
        ids_str = [str(sid) for sid in sample_ids]

        response = (
            self.client.table(self.table_name)
            .select("*")
            .in_("id", ids_str)
            .execute()
        )

        samples = [DatasetSample(**item) for item in response.data]
        logger.debug(f"Retrieved {len(samples)} samples")
        return samples

    def get_validated_samples(self) -> list[DatasetSample]:
        """Get all validated samples (auto or manually validated).

        Returns:
            List of validated DatasetSample objects
        """
        logger.debug("Fetching all validated samples")

        response = (
            self.client.table(self.table_name)
            .select("*")
            .in_(
                "status",
                [
                    SampleStatus.AUTO_VALIDATED.value,
                    SampleStatus.MANUALLY_VALIDATED.value,
                ],
            )
            .execute()
        )

        samples = [DatasetSample(**item) for item in response.data]
        logger.info(f"Retrieved {len(samples)} validated samples")
        return samples

    def reset_samples(self, sample_ids: Optional[list[str]] = None) -> int:
        """Reset samples to pending status, clearing all extraction results.

        This keeps the PDF files in storage but clears all processing data,
        allowing samples to be reprocessed through the pipeline.

        Args:
            sample_ids: Optional list of specific sample IDs to reset.
                       If None, resets ALL samples.

        Returns:
            Number of samples reset
        """
        logger.warning(
            f"Resetting samples to pending: "
            f"{'specific IDs' if sample_ids else 'ALL samples'}"
        )

        # Fields to clear (set to None/pending)
        reset_data = {
            "status": SampleStatus.PENDING.value,
            "datalab_raw_ocr": None,
            "datalab_json": None,
            "datalab_processing_time_ms": None,
            "datalab_error": None,
            "azure_raw_ocr": None,
            "azure_processing_time_ms": None,
            "azure_error": None,
            "gemini_json": None,
            "gemini_processing_time_ms": None,
            "gemini_error": None,
            "match_score": None,
            "discrepancies": None,
            "validated_output": None,
            "validation_source": None,
            "validator_notes": None,
            "dataset_split": None,
        }

        if sample_ids:
            # Reset specific samples
            response = (
                self.client.table(self.table_name)
                .update(reset_data)
                .in_("id", sample_ids)
                .execute()
            )
        else:
            # Reset all samples - need to use a condition that matches all
            response = (
                self.client.table(self.table_name)
                .update(reset_data)
                .neq("id", "00000000-0000-0000-0000-000000000000")  # Matches all real UUIDs
                .execute()
            )

        count = len(response.data) if response.data else 0
        logger.info(f"Reset {count} samples to pending status")
        return count


class StatsRepository:
    """Repository for managing processing statistics.

    This class provides methods for reading and updating global processing
    statistics. The processing_stats table is a single-row table.
    """

    def __init__(self):
        """Initialize the repository with a Supabase client."""
        self.client = get_client()
        self.table_name = "processing_stats"

    def get_stats(self) -> ProcessingStats:
        """Get the current processing statistics.

        Returns:
            ProcessingStats object with current statistics

        Raises:
            Exception: If stats row doesn't exist
        """
        logger.debug("Fetching processing stats")

        response = self.client.table(self.table_name).select("*").limit(1).execute()

        if not response.data or len(response.data) == 0:
            raise Exception("Processing stats row not found in database")

        stats = ProcessingStats(**response.data[0])
        logger.debug(
            f"Stats retrieved: {stats.processed}/{stats.total_samples} processed"
        )
        return stats

    def update_stats(self, **fields: Any) -> ProcessingStats:
        """Update processing statistics with the given fields.

        Args:
            **fields: Field names and values to update

        Returns:
            Updated ProcessingStats

        Raises:
            Exception: If update fails

        Example:
            >>> repo = StatsRepository()
            >>> stats = repo.update_stats(
            ...     total_samples=100,
            ...     processed=50,
            ...     is_processing=True
            ... )
        """
        logger.info(f"Updating stats with fields: {list(fields.keys())}")

        # Get the current stats to know the ID
        current_stats = self.get_stats()

        response = (
            self.client.table(self.table_name)
            .update(fields)
            .eq("id", str(current_stats.id))
            .execute()
        )

        if not response.data or len(response.data) == 0:
            raise Exception("Failed to update processing stats")

        updated_stats = ProcessingStats(**response.data[0])
        logger.info("Stats updated successfully")
        return updated_stats

    def increment_counters(self, **counters: int) -> ProcessingStats:
        """Increment one or more counter fields.

        This method fetches current stats, increments the specified counters,
        and saves them back. It's not atomic but sufficient for this use case.

        Args:
            **counters: Counter field names and increment values

        Returns:
            Updated ProcessingStats

        Example:
            >>> repo = StatsRepository()
            >>> stats = repo.increment_counters(
            ...     processed=1,
            ...     auto_validated=1
            ... )
        """
        logger.info(f"Incrementing counters: {counters}")

        # Get current stats
        current_stats = self.get_stats()

        # Calculate new values
        updates = {}
        for field, increment in counters.items():
            current_value = getattr(current_stats, field, 0)
            updates[field] = current_value + increment

        # Update and return
        return self.update_stats(**updates)

    def reset_stats(self) -> ProcessingStats:
        """Reset all statistics to zero (except is_processing flag).

        Returns:
            Reset ProcessingStats

        Warning:
            This will clear all statistics. Use with caution.
        """
        logger.warning("Resetting all processing stats to zero")

        return self.update_stats(
            total_samples=0,
            processed=0,
            auto_validated=0,
            needs_review=0,
            manually_validated=0,
            rejected=0,
            errors=0,
            avg_match_score=None,
            total_processing_time_ms=None,
            is_processing=False,
        )

    def set_processing_flag(self, is_processing: bool) -> ProcessingStats:
        """Set the is_processing flag.

        Args:
            is_processing: Whether processing is currently running

        Returns:
            Updated ProcessingStats
        """
        logger.info(f"Setting is_processing flag to: {is_processing}")
        return self.update_stats(is_processing=is_processing)
