# Database Module

This module provides the database layer for the DDT Dataset Generator, including models, repositories, and storage operations for Supabase.

## Overview

The database module is organized into the following components:

- **client.py**: Singleton Supabase client with service role authentication
- **models.py**: Pydantic models for type-safe database operations
- **repository.py**: Repository pattern for database operations
- **storage.py**: Supabase Storage operations for PDF files

## Quick Start

```python
from src.database import (
    SampleRepository,
    StatsRepository,
    SampleStatus,
    upload_pdf,
    get_pdf_url,
)

# Create a sample repository
repo = SampleRepository()

# Upload a PDF
with open("sample.pdf", "rb") as f:
    storage_path = upload_pdf(f.read(), "sample.pdf")

# Create a database record
sample = repo.create_sample(
    filename="sample.pdf",
    pdf_path=storage_path,
    file_size=1024
)

# Update the sample
updated = repo.update_sample(
    sample.id,
    status=SampleStatus.PROCESSING,
    datalab_raw_ocr="Raw OCR text..."
)

# Get statistics
stats_repo = StatsRepository()
stats = stats_repo.get_stats()
print(f"Progress: {stats.progress_percent}%")
```

## Models

### DatasetSample

Represents a single DDT PDF sample with all processing data.

**Key fields:**
- `id`: UUID primary key
- `filename`: Original PDF filename
- `pdf_storage_path`: Path in Supabase Storage
- `status`: Current processing status (enum)
- `datalab_json`: Extracted data from Datalab
- `gemini_json`: Extracted data from Gemini
- `match_score`: Similarity score (0.0-1.0)
- `validated_output`: Final validated JSON output

### ProcessingStats

Global processing statistics (single-row table).

**Key fields:**
- `total_samples`: Total uploaded samples
- `processed`: Number of processed samples
- `auto_validated`: Number of auto-validated samples
- `needs_review`: Number requiring manual review
- `is_processing`: Whether processing is running

**Properties:**
- `progress_percent`: Calculated progress (0-100)
- `validation_breakdown`: Dictionary of validation statuses

### Enums

- **SampleStatus**: `pending`, `processing`, `auto_validated`, `needs_review`, `manually_validated`, `rejected`, `error`
- **ValidationSource**: `datalab`, `gemini`, `manual`
- **DatasetSplit**: `train`, `validation`

## Repositories

### SampleRepository

Repository for managing dataset samples.

**Methods:**

- `create_sample(filename, pdf_path, file_size)`: Create a new sample
- `get_sample(sample_id)`: Get a sample by ID
- `get_samples(status, limit, offset)`: List samples with filters
- `update_sample(sample_id, **fields)`: Update a sample
- `count_by_status()`: Count samples by status
- `get_validated_samples()`: Get all validated samples

**Example:**

```python
repo = SampleRepository()

# Create
sample = repo.create_sample(
    filename="ddt_001.pdf",
    pdf_path="uploads/abc-123.pdf",
    file_size=524288
)

# Read
sample = repo.get_sample(sample_id)
samples = repo.get_samples(status=SampleStatus.NEEDS_REVIEW, limit=10)

# Update
updated = repo.update_sample(
    sample_id,
    status=SampleStatus.AUTO_VALIDATED,
    validated_output={"mittente": "LAVAZZA", ...}
)

# Count
counts = repo.count_by_status()
# {"pending": 5, "processing": 2, "auto_validated": 10, ...}
```

### StatsRepository

Repository for managing processing statistics.

**Methods:**

- `get_stats()`: Get current statistics
- `update_stats(**fields)`: Update statistics
- `increment_counters(**counters)`: Increment counter fields
- `set_processing_flag(is_processing)`: Set processing flag
- `reset_stats()`: Reset all statistics to zero

**Example:**

```python
repo = StatsRepository()

# Get stats
stats = repo.get_stats()
print(f"Progress: {stats.progress_percent}%")

# Increment counters
stats = repo.increment_counters(processed=1, auto_validated=1)

# Set processing flag
stats = repo.set_processing_flag(True)
```

## Storage Operations

Functions for managing PDF files in Supabase Storage.

### upload_pdf(file_bytes, filename)

Upload a PDF file to storage.

**Parameters:**
- `file_bytes`: Binary content of the PDF
- `filename`: Original filename

**Returns:**
- `str`: Storage path (e.g., "uploads/{uuid}.pdf")

**Example:**

```python
with open("sample.pdf", "rb") as f:
    storage_path = upload_pdf(f.read(), "sample.pdf")
```

### get_pdf_url(storage_path, expires_in)

Get a signed URL for accessing a PDF.

**Parameters:**
- `storage_path`: Storage path of the file
- `expires_in`: URL expiration in seconds (default: 3600)

**Returns:**
- `str`: Signed URL

**Example:**

```python
url = get_pdf_url("uploads/abc-123.pdf", expires_in=3600)
```

### delete_pdf(storage_path)

Delete a PDF file from storage.

**Parameters:**
- `storage_path`: Storage path of the file

**Returns:**
- `bool`: True if successful

**Example:**

```python
success = delete_pdf("uploads/abc-123.pdf")
```

## Database Schema

The module works with the following Supabase tables:

### dataset_samples

Main table storing all PDF samples and processing results.

**Columns:**
- Primary key: `id` (UUID)
- Timestamps: `created_at`, `updated_at`
- File info: `filename`, `pdf_storage_path`, `file_size_bytes`
- Datalab pipeline: `datalab_raw_ocr`, `datalab_json`, `datalab_processing_time_ms`, `datalab_error`
- Azure+Gemini pipeline: `azure_raw_ocr`, `gemini_json`, processing times, errors
- Comparison: `match_score`, `discrepancies`
- Validation: `status`, `validated_output`, `validation_source`, `validator_notes`
- Dataset: `dataset_split`

**Indexes:**
- `idx_samples_status` on `status`
- `idx_samples_match_score` on `match_score`
- `idx_samples_created_at` on `created_at DESC`

### processing_stats

Single-row table for global statistics.

**Columns:**
- Primary key: `id` (UUID)
- Timestamps: `created_at`, `updated_at`
- Counters: `total_samples`, `processed`, `auto_validated`, `needs_review`, etc.
- Metrics: `avg_match_score`, `total_processing_time_ms`
- Flag: `is_processing`

## Configuration

The database module uses environment variables from `config.py`:

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_BUCKET=dataset-pdfs
```

**Important:** The module uses the `SUPABASE_SERVICE_KEY` to bypass Row Level Security (RLS) for backend operations.

## Client Architecture

The Supabase client uses a singleton pattern to ensure only one connection instance is created and reused throughout the application.

```python
from src.database import get_client, get_storage

# Get client instance (creates on first call, reuses after)
client = get_client()

# Get storage client for PDFs bucket
storage = get_storage()
```

## Testing

### Unit Tests

Run the unit tests with mocked Supabase client:

```bash
cd backend
pytest tests/test_database.py -v
```

### Integration Tests

Run integration tests with real Supabase (requires valid credentials):

```bash
cd backend
python test_integration_db.py
```

This will:
1. Test connection to Supabase
2. Test StatsRepository operations
3. Test SampleRepository CRUD operations
4. Test Storage upload/download/delete

## Error Handling

All repository and storage functions include comprehensive error handling:

- Database operations raise exceptions on failure
- Storage operations return `None` or `False` on failure
- All errors are logged with the `logging` module

**Example:**

```python
try:
    sample = repo.create_sample(filename, path, size)
except Exception as e:
    logger.error(f"Failed to create sample: {e}")
    # Handle error appropriately
```

## Best Practices

1. **Always use repositories**: Don't access the Supabase client directly in business logic
2. **Use enums for status fields**: Ensures type safety and prevents typos
3. **Handle None returns**: Repository methods may return `None` if records aren't found
4. **Log operations**: All operations are logged for debugging
5. **Use transactions carefully**: Supabase Python client doesn't support transactions yet
6. **Clean up storage**: Delete PDFs when samples are rejected

## Common Patterns

### Creating a sample from uploaded PDF

```python
# Upload PDF
storage_path = upload_pdf(pdf_bytes, filename)

# Create database record
sample = repo.create_sample(
    filename=filename,
    pdf_path=storage_path,
    file_size=len(pdf_bytes)
)
```

### Processing pipeline updates

```python
# Mark as processing
repo.update_sample(sample_id, status=SampleStatus.PROCESSING)

# Update with Datalab results
repo.update_sample(
    sample_id,
    datalab_raw_ocr=ocr_text,
    datalab_json=extracted_data,
    datalab_processing_time_ms=elapsed_ms
)

# Update with comparison results
repo.update_sample(
    sample_id,
    match_score=score,
    discrepancies=discrepancies,
    status=SampleStatus.AUTO_VALIDATED if score >= 0.95 else SampleStatus.NEEDS_REVIEW,
    validated_output=output_data
)
```

### Manual validation workflow

```python
# Get sample for review
sample = repo.get_sample(sample_id)

# Get PDF URL for viewing
pdf_url = get_pdf_url(sample.pdf_storage_path)

# Manual validation
repo.update_sample(
    sample_id,
    status=SampleStatus.MANUALLY_VALIDATED,
    validated_output=corrected_data,
    validation_source=ValidationSource.MANUAL,
    validator_notes="Corrected numero_documento field"
)
```

## Documentation References

- [Supabase Python Client](https://supabase.com/docs/reference/python/introduction)
- [Supabase Storage Guide](https://supabase.com/docs/guides/storage)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

For more information, see:
- `/Users/franzoai/ddt-dataset-generator/PRD.md` - Full product requirements
- `/Users/franzoai/ddt-dataset-generator/backend/supabase_schema.sql` - Database schema
