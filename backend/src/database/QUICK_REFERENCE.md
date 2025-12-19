# Database Module - Quick Reference Card

## Import Everything You Need

```python
from src.database import (
    # Client
    get_client, get_storage,

    # Models
    DatasetSample, ProcessingStats,

    # Enums
    SampleStatus, ValidationSource, DatasetSplit,

    # Repositories
    SampleRepository, StatsRepository,

    # Storage
    upload_pdf, get_pdf_url, delete_pdf,
)
```

## Common Operations

### Upload & Create Sample

```python
# Upload PDF to storage
with open("ddt_001.pdf", "rb") as f:
    pdf_bytes = f.read()
    storage_path = upload_pdf(pdf_bytes, "ddt_001.pdf")

# Create database record
repo = SampleRepository()
sample = repo.create_sample(
    filename="ddt_001.pdf",
    pdf_path=storage_path,
    file_size=len(pdf_bytes)
)
```

### Update Sample with Processing Results

```python
# Update Datalab results
sample = repo.update_sample(
    sample_id,
    datalab_raw_ocr="OCR text...",
    datalab_json={"mittente": "LAVAZZA", ...},
    datalab_processing_time_ms=8500
)

# Update Gemini results
sample = repo.update_sample(
    sample_id,
    gemini_json={"mittente": "LAVAZZA", ...},
    gemini_processing_time_ms=2100
)

# Update comparison results
sample = repo.update_sample(
    sample_id,
    match_score=0.9875,
    discrepancies=["data_trasporto"],
    status=SampleStatus.AUTO_VALIDATED,
    validated_output={"mittente": "LAVAZZA", ...},
    validation_source=ValidationSource.DATALAB
)
```

### Query Samples

```python
# Get by ID
sample = repo.get_sample(sample_id)

# Get samples needing review
needs_review = repo.get_samples(
    status=SampleStatus.NEEDS_REVIEW,
    limit=10,
    offset=0
)

# Get all validated samples
validated = repo.get_validated_samples()

# Count by status
counts = repo.count_by_status()
# {"pending": 5, "auto_validated": 100, ...}
```

### Statistics

```python
stats_repo = StatsRepository()

# Get current stats
stats = stats_repo.get_stats()
print(f"Progress: {stats.progress_percent}%")
print(f"Validated: {stats.auto_validated + stats.manually_validated}")

# Update stats
stats = stats_repo.update_stats(
    total_samples=100,
    is_processing=True
)

# Increment counters
stats = stats_repo.increment_counters(
    processed=1,
    auto_validated=1
)

# Set processing flag
stats = stats_repo.set_processing_flag(True)
```

### Storage Operations

```python
# Get PDF URL for viewing
url = get_pdf_url(sample.pdf_storage_path, expires_in=3600)

# Download PDF bytes
pdf_bytes = get_pdf_bytes(sample.pdf_storage_path)

# Delete PDF
success = delete_pdf(sample.pdf_storage_path)
```

## Status Flow

```
pending → processing → auto_validated (score >= 0.95)
                    → needs_review (score < 0.95)
                                  → manually_validated
                                  → rejected
                    → error
```

## Status Values

```python
SampleStatus.PENDING              # Initial state
SampleStatus.PROCESSING           # Currently being processed
SampleStatus.AUTO_VALIDATED       # Auto-validated (score >= 0.95)
SampleStatus.NEEDS_REVIEW         # Needs manual review
SampleStatus.MANUALLY_VALIDATED   # Manually validated by user
SampleStatus.REJECTED             # Rejected sample
SampleStatus.ERROR                # Processing error
```

## Validation Sources

```python
ValidationSource.DATALAB  # Used Datalab output
ValidationSource.GEMINI   # Used Gemini output
ValidationSource.MANUAL   # Manually entered/corrected
```

## Dataset Splits

```python
DatasetSplit.TRAIN       # Training set
DatasetSplit.VALIDATION  # Validation set
```

## Processing Pipeline Example

```python
from src.database import (
    SampleRepository, StatsRepository,
    SampleStatus, ValidationSource,
    upload_pdf
)

# 1. Upload PDF
storage_path = upload_pdf(pdf_bytes, filename)

# 2. Create sample
repo = SampleRepository()
sample = repo.create_sample(filename, storage_path, len(pdf_bytes))

# 3. Mark as processing
repo.update_sample(sample.id, status=SampleStatus.PROCESSING)

# 4. Process with Datalab
datalab_result = process_with_datalab(pdf_bytes)
repo.update_sample(
    sample.id,
    datalab_raw_ocr=datalab_result["ocr"],
    datalab_json=datalab_result["json"],
    datalab_processing_time_ms=datalab_result["time"]
)

# 5. Process with Azure + Gemini
azure_ocr = process_with_azure(pdf_bytes)
gemini_result = process_with_gemini(azure_ocr)
repo.update_sample(
    sample.id,
    azure_raw_ocr=azure_ocr,
    gemini_json=gemini_result["json"],
    gemini_processing_time_ms=gemini_result["time"]
)

# 6. Compare results
match_score, discrepancies = compare_outputs(
    datalab_result["json"],
    gemini_result["json"]
)

# 7. Auto-validate or flag for review
if match_score >= 0.95:
    status = SampleStatus.AUTO_VALIDATED
    validated = datalab_result["json"]  # Default to Datalab
    source = ValidationSource.DATALAB
else:
    status = SampleStatus.NEEDS_REVIEW
    validated = None
    source = None

repo.update_sample(
    sample.id,
    match_score=match_score,
    discrepancies=discrepancies,
    status=status,
    validated_output=validated,
    validation_source=source
)

# 8. Update statistics
stats_repo = StatsRepository()
stats_repo.increment_counters(
    processed=1,
    auto_validated=1 if status == SampleStatus.AUTO_VALIDATED else 0,
    needs_review=1 if status == SampleStatus.NEEDS_REVIEW else 0
)
```

## Manual Validation Example

```python
# 1. Get sample for review
sample = repo.get_sample(sample_id)

# 2. Get PDF URL for frontend
pdf_url = get_pdf_url(sample.pdf_storage_path)

# 3. User reviews and corrects data
corrected_data = {
    "mittente": "LAVAZZA S.p.A.",  # Corrected
    "destinatario": sample.gemini_json["destinatario"],
    # ... other fields
}

# 4. Save validated output
repo.update_sample(
    sample_id,
    status=SampleStatus.MANUALLY_VALIDATED,
    validated_output=corrected_data,
    validation_source=ValidationSource.MANUAL,
    validator_notes="Corrected mittente field from Datalab output"
)

# 5. Update stats
stats_repo.increment_counters(
    manually_validated=1,
    needs_review=-1
)
```

## Error Handling

```python
try:
    sample = repo.create_sample(filename, path, size)
except Exception as e:
    logger.error(f"Failed to create sample: {e}")
    # Handle error

# Check if sample exists
sample = repo.get_sample(sample_id)
if sample is None:
    # Sample not found
    pass

# Check if file exists
if check_file_exists(storage_path):
    # File exists
    pass
```

## Testing

```bash
# Unit tests (with mocks)
pytest tests/test_database.py -v

# Integration tests (real Supabase)
python test_integration_db.py
```

## Key Files

- **models.py**: DatasetSample, ProcessingStats, Enums
- **repository.py**: SampleRepository, StatsRepository
- **storage.py**: upload_pdf, get_pdf_url, delete_pdf
- **client.py**: get_client, get_storage

## Environment Variables

```env
SUPABASE_URL=https://iexbwkjjtxhragdkoxmi.supabase.co
SUPABASE_SERVICE_KEY=eyJ...  # Service role key
SUPABASE_BUCKET=dataset-pdfs
```

## Tips

1. Always use repositories, not direct client access
2. Use enums for status fields (type safety)
3. Handle None returns (sample not found)
4. Log all operations
5. Clean up storage when rejecting samples
6. Update stats after batch operations

---

For full documentation, see `/Users/franzoai/ddt-dataset-generator/backend/src/database/README.md`
