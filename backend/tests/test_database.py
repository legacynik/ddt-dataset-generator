"""Tests for database operations.

This module tests the database layer including client initialization,
models, repositories, and storage operations.
"""

import json
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from src.database import (
    DatasetSample,
    DatasetSplit,
    ProcessingStats,
    SampleRepository,
    SampleStatus,
    StatsRepository,
    ValidationSource,
    delete_pdf,
    get_client,
    get_pdf_url,
    get_storage,
    upload_pdf,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_id():
    """Return a sample UUID for testing."""
    return uuid4()


@pytest.fixture
def sample_data(sample_id):
    """Return sample data for testing."""
    return {
        "id": str(sample_id),
        "created_at": "2025-12-17T10:00:00Z",
        "updated_at": "2025-12-17T10:00:00Z",
        "filename": "ddt_001.pdf",
        "pdf_storage_path": f"uploads/{sample_id}.pdf",
        "file_size_bytes": 524288,
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
        "status": "pending",
        "validated_output": None,
        "validation_source": None,
        "validator_notes": None,
        "dataset_split": None,
    }


@pytest.fixture
def stats_data():
    """Return stats data for testing."""
    return {
        "id": str(uuid4()),
        "created_at": "2025-12-17T09:00:00Z",
        "updated_at": "2025-12-17T10:00:00Z",
        "total_samples": 100,
        "processed": 80,
        "auto_validated": 70,
        "needs_review": 8,
        "manually_validated": 2,
        "rejected": 0,
        "errors": 0,
        "avg_match_score": 0.943,
        "total_processing_time_ms": 1200000,
        "is_processing": False,
    }


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    mock_client = MagicMock()

    # Mock table operations
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    # Mock storage operations
    mock_storage = MagicMock()
    mock_client.storage = mock_storage

    return mock_client


# ============================================================================
# Client Tests
# ============================================================================


def test_get_client():
    """Test that get_client returns a Supabase client."""
    # We can't fully test this without real credentials,
    # but we can verify the function exists and returns something
    with patch("src.database.client.create_client") as mock_create:
        mock_create.return_value = MagicMock()

        client = get_client()

        assert client is not None
        mock_create.assert_called_once()


def test_get_storage():
    """Test that get_storage returns a storage client."""
    with patch("src.database.client.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_client.storage.from_.return_value = mock_storage
        mock_get_client.return_value = mock_client

        storage = get_storage()

        assert storage is not None
        mock_client.storage.from_.assert_called_once_with("dataset-pdfs")


# ============================================================================
# Model Tests
# ============================================================================


def test_dataset_sample_model(sample_data):
    """Test DatasetSample model creation and validation."""
    sample = DatasetSample(**sample_data)

    assert sample.filename == "ddt_001.pdf"
    assert sample.status == SampleStatus.PENDING
    assert sample.file_size_bytes == 524288


def test_dataset_sample_with_json_fields(sample_data):
    """Test DatasetSample with JSON fields."""
    sample_data["datalab_json"] = {
        "mittente": "LAVAZZA S.p.A.",
        "destinatario": "CONAD",
    }
    sample_data["validated_output"] = sample_data["datalab_json"]

    sample = DatasetSample(**sample_data)

    assert sample.datalab_json["mittente"] == "LAVAZZA S.p.A."
    assert sample.validated_output is not None


def test_dataset_sample_match_score_conversion(sample_data):
    """Test that match_score is properly converted to Decimal."""
    # Test with float
    sample_data["match_score"] = 0.9875
    sample = DatasetSample(**sample_data)
    assert isinstance(sample.match_score, Decimal)
    assert sample.match_score == Decimal("0.9875")

    # Test with string
    sample_data["match_score"] = "0.95"
    sample = DatasetSample(**sample_data)
    assert isinstance(sample.match_score, Decimal)


def test_processing_stats_model(stats_data):
    """Test ProcessingStats model creation and validation."""
    stats = ProcessingStats(**stats_data)

    assert stats.total_samples == 100
    assert stats.processed == 80
    assert stats.is_processing is False


def test_processing_stats_progress_percent(stats_data):
    """Test progress percentage calculation."""
    stats = ProcessingStats(**stats_data)
    assert stats.progress_percent == 80.0

    # Test with zero samples
    stats_data["total_samples"] = 0
    stats = ProcessingStats(**stats_data)
    assert stats.progress_percent == 0.0


def test_processing_stats_validation_breakdown(stats_data):
    """Test validation breakdown property."""
    stats = ProcessingStats(**stats_data)
    breakdown = stats.validation_breakdown

    assert breakdown["auto_validated"] == 70
    assert breakdown["needs_review"] == 8
    assert breakdown["manually_validated"] == 2
    assert breakdown["rejected"] == 0
    assert breakdown["errors"] == 0


def test_sample_status_enum():
    """Test SampleStatus enum values."""
    assert SampleStatus.PENDING.value == "pending"
    assert SampleStatus.PROCESSING.value == "processing"
    assert SampleStatus.AUTO_VALIDATED.value == "auto_validated"
    assert SampleStatus.NEEDS_REVIEW.value == "needs_review"
    assert SampleStatus.MANUALLY_VALIDATED.value == "manually_validated"
    assert SampleStatus.REJECTED.value == "rejected"
    assert SampleStatus.ERROR.value == "error"


def test_validation_source_enum():
    """Test ValidationSource enum values."""
    assert ValidationSource.DATALAB.value == "datalab"
    assert ValidationSource.GEMINI.value == "gemini"
    assert ValidationSource.MANUAL.value == "manual"


def test_dataset_split_enum():
    """Test DatasetSplit enum values."""
    assert DatasetSplit.TRAIN.value == "train"
    assert DatasetSplit.VALIDATION.value == "validation"


# ============================================================================
# SampleRepository Tests
# ============================================================================


@patch("src.database.repository.get_client")
def test_sample_repository_create(mock_get_client, sample_data):
    """Test creating a new sample."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [sample_data]

    mock_client.table.return_value.insert.return_value.execute.return_value = (
        mock_response
    )
    mock_get_client.return_value = mock_client

    repo = SampleRepository()
    sample = repo.create_sample(
        filename="ddt_001.pdf",
        pdf_path=f"uploads/{sample_data['id']}.pdf",
        file_size=524288,
    )

    assert sample.filename == "ddt_001.pdf"
    assert sample.status == SampleStatus.PENDING
    mock_client.table.assert_called_with("dataset_samples")


@patch("src.database.repository.get_client")
def test_sample_repository_get_sample(mock_get_client, sample_data, sample_id):
    """Test getting a sample by ID."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [sample_data]

    (
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value
    ) = mock_response
    mock_get_client.return_value = mock_client

    repo = SampleRepository()
    sample = repo.get_sample(sample_id)

    assert sample is not None
    assert sample.filename == "ddt_001.pdf"


@patch("src.database.repository.get_client")
def test_sample_repository_get_sample_not_found(mock_get_client):
    """Test getting a non-existent sample."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = []

    (
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value
    ) = mock_response
    mock_get_client.return_value = mock_client

    repo = SampleRepository()
    sample = repo.get_sample(uuid4())

    assert sample is None


@patch("src.database.repository.get_client")
def test_sample_repository_get_samples(mock_get_client, sample_data):
    """Test getting a list of samples."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [sample_data, sample_data]

    mock_query = MagicMock()
    mock_query.order.return_value.range.return_value.execute.return_value = (
        mock_response
    )
    mock_client.table.return_value.select.return_value = mock_query

    mock_get_client.return_value = mock_client

    repo = SampleRepository()
    samples = repo.get_samples(limit=10, offset=0)

    assert len(samples) == 2
    assert samples[0].filename == "ddt_001.pdf"


@patch("src.database.repository.get_client")
def test_sample_repository_get_samples_with_status_filter(
    mock_get_client, sample_data
):
    """Test getting samples filtered by status."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [sample_data]

    mock_query = MagicMock()
    mock_query.eq.return_value.order.return_value.range.return_value.execute.return_value = (
        mock_response
    )
    mock_client.table.return_value.select.return_value = mock_query

    mock_get_client.return_value = mock_client

    repo = SampleRepository()
    samples = repo.get_samples(status=SampleStatus.PENDING)

    assert len(samples) == 1
    mock_query.eq.assert_called_with("status", "pending")


@patch("src.database.repository.get_client")
def test_sample_repository_update(mock_get_client, sample_data, sample_id):
    """Test updating a sample."""
    mock_client = MagicMock()

    # Update status to processing
    updated_data = sample_data.copy()
    updated_data["status"] = "processing"

    mock_response = MagicMock()
    mock_response.data = [updated_data]

    (
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value
    ) = mock_response
    mock_get_client.return_value = mock_client

    repo = SampleRepository()
    sample = repo.update_sample(sample_id, status=SampleStatus.PROCESSING)

    assert sample.status == SampleStatus.PROCESSING


@patch("src.database.repository.get_client")
def test_sample_repository_count_by_status(mock_get_client, sample_data):
    """Test counting samples by status."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [
        {"status": "pending"},
        {"status": "pending"},
        {"status": "processing"},
        {"status": "auto_validated"},
    ]

    mock_client.table.return_value.select.return_value.execute.return_value = (
        mock_response
    )
    mock_get_client.return_value = mock_client

    repo = SampleRepository()
    counts = repo.count_by_status()

    assert counts["pending"] == 2
    assert counts["processing"] == 1
    assert counts["auto_validated"] == 1


@patch("src.database.repository.get_client")
def test_sample_repository_get_validated_samples(mock_get_client, sample_data):
    """Test getting validated samples."""
    mock_client = MagicMock()
    mock_response = MagicMock()

    validated_sample = sample_data.copy()
    validated_sample["status"] = "auto_validated"

    mock_response.data = [validated_sample]

    (
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value
    ) = mock_response
    mock_get_client.return_value = mock_client

    repo = SampleRepository()
    samples = repo.get_validated_samples()

    assert len(samples) == 1
    assert samples[0].status == SampleStatus.AUTO_VALIDATED


# ============================================================================
# StatsRepository Tests
# ============================================================================


@patch("src.database.repository.get_client")
def test_stats_repository_get_stats(mock_get_client, stats_data):
    """Test getting processing stats."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [stats_data]

    (
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value
    ) = mock_response
    mock_get_client.return_value = mock_client

    repo = StatsRepository()
    stats = repo.get_stats()

    assert stats.total_samples == 100
    assert stats.processed == 80


@patch("src.database.repository.get_client")
def test_stats_repository_update_stats(mock_get_client, stats_data):
    """Test updating processing stats."""
    mock_client = MagicMock()

    # Mock get_stats
    get_response = MagicMock()
    get_response.data = [stats_data]

    # Mock update
    updated_data = stats_data.copy()
    updated_data["processed"] = 90

    update_response = MagicMock()
    update_response.data = [updated_data]

    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
        get_response
    )
    (
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value
    ) = update_response

    mock_get_client.return_value = mock_client

    repo = StatsRepository()
    stats = repo.update_stats(processed=90)

    assert stats.processed == 90


@patch("src.database.repository.get_client")
def test_stats_repository_increment_counters(mock_get_client, stats_data):
    """Test incrementing stat counters."""
    mock_client = MagicMock()

    # Mock get_stats
    get_response = MagicMock()
    get_response.data = [stats_data]

    # Mock update
    updated_data = stats_data.copy()
    updated_data["processed"] = 81
    updated_data["auto_validated"] = 71

    update_response = MagicMock()
    update_response.data = [updated_data]

    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
        get_response
    )
    (
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value
    ) = update_response

    mock_get_client.return_value = mock_client

    repo = StatsRepository()
    stats = repo.increment_counters(processed=1, auto_validated=1)

    assert stats.processed == 81
    assert stats.auto_validated == 71


@patch("src.database.repository.get_client")
def test_stats_repository_set_processing_flag(mock_get_client, stats_data):
    """Test setting the is_processing flag."""
    mock_client = MagicMock()

    # Mock get_stats
    get_response = MagicMock()
    get_response.data = [stats_data]

    # Mock update
    updated_data = stats_data.copy()
    updated_data["is_processing"] = True

    update_response = MagicMock()
    update_response.data = [updated_data]

    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
        get_response
    )
    (
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value
    ) = update_response

    mock_get_client.return_value = mock_client

    repo = StatsRepository()
    stats = repo.set_processing_flag(True)

    assert stats.is_processing is True


# ============================================================================
# Storage Tests
# ============================================================================


@patch("src.database.storage.get_storage")
def test_upload_pdf(mock_get_storage):
    """Test uploading a PDF to storage."""
    mock_storage = MagicMock()
    mock_storage.upload.return_value = {"path": "uploads/test.pdf"}
    mock_get_storage.return_value = mock_storage

    pdf_bytes = b"fake pdf content"
    storage_path = upload_pdf(pdf_bytes, "test.pdf")

    assert storage_path.startswith("uploads/")
    assert storage_path.endswith(".pdf")
    mock_storage.upload.assert_called_once()


@patch("src.database.storage.get_storage")
def test_get_pdf_url(mock_get_storage):
    """Test getting a signed URL for a PDF."""
    mock_storage = MagicMock()
    mock_storage.create_signed_url.return_value = {
        "signedURL": "https://example.com/signed-url"
    }
    mock_get_storage.return_value = mock_storage

    url = get_pdf_url("uploads/test.pdf")

    assert url == "https://example.com/signed-url"
    mock_storage.create_signed_url.assert_called_once()


@patch("src.database.storage.get_storage")
def test_delete_pdf(mock_get_storage):
    """Test deleting a PDF from storage."""
    mock_storage = MagicMock()
    mock_storage.remove.return_value = {"message": "Success"}
    mock_get_storage.return_value = mock_storage

    result = delete_pdf("uploads/test.pdf")

    assert result is True
    mock_storage.remove.assert_called_once_with(["uploads/test.pdf"])


@patch("src.database.storage.get_storage")
def test_upload_pdf_failure(mock_get_storage):
    """Test upload failure handling."""
    mock_storage = MagicMock()
    mock_storage.upload.side_effect = Exception("Upload failed")
    mock_get_storage.return_value = mock_storage

    pdf_bytes = b"fake pdf content"

    with pytest.raises(Exception) as exc_info:
        upload_pdf(pdf_bytes, "test.pdf")

    assert "Failed to upload PDF to storage" in str(exc_info.value)


@patch("src.database.storage.get_storage")
def test_get_pdf_url_failure(mock_get_storage):
    """Test URL generation failure handling."""
    mock_storage = MagicMock()
    mock_storage.create_signed_url.side_effect = Exception("URL generation failed")
    mock_get_storage.return_value = mock_storage

    with pytest.raises(Exception) as exc_info:
        get_pdf_url("uploads/test.pdf")

    assert "Failed to generate PDF URL" in str(exc_info.value)
