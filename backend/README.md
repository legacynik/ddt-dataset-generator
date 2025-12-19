# DDT Dataset Generator - Backend

FastAPI backend service for processing Italian DDT (Documento di Trasporto) documents and generating training datasets.

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or using poetry
poetry install
```

### Running the Server

```bash
# Development mode with auto-reload
uvicorn src.main:app --reload --port 8000

# Or using Python module
python -m uvicorn src.main:app --reload --port 8000
```

### Testing

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## Project Structure

```
backend/
├── pyproject.toml          # Poetry dependencies
├── requirements.txt        # Pip dependencies
├── src/
│   ├── __init__.py
│   ├── config.py          # Environment configuration
│   ├── main.py            # FastAPI application
│   ├── api/               # API routes (TODO)
│   ├── database/          # Database client (TODO)
│   ├── extractors/        # PDF extraction logic (TODO)
│   └── processing/        # Data processing pipeline (TODO)
└── tests/                 # Unit and integration tests
```

## Configuration

All configuration is loaded from environment variables defined in `.env` file at project root.

### Required Environment Variables

See `/Users/franzoai/ddt-dataset-generator/.env` for the complete list:

- **Datalab**: `DATALAB_API_KEY`, `DATALAB_API_URL`
- **Azure**: `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`, `AZURE_DOCUMENT_INTELLIGENCE_KEY`
- **Google**: `GOOGLE_API_KEY`, `GEMINI_MODEL`
- **Supabase**: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_BUCKET`
- **App Config**: `LOG_LEVEL`, `MAX_PARALLEL_PDFS`, `ENVIRONMENT`

## API Endpoints

### Current

- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint

### Planned (M2-M4)

- `POST /api/upload` - Upload PDF files
- `POST /api/process` - Start batch processing
- `GET /api/status` - Processing progress
- `GET /api/samples` - List all samples
- `GET /api/samples/{id}` - Sample detail
- `PATCH /api/samples/{id}` - Manual validation
- `POST /api/export` - Generate JSONL dataset

## Development

### Code Style

- Follow Python type hints
- Use async/await for I/O operations
- Follow naming conventions: snake_case for files/functions, PascalCase for classes
- Maximum line length: 100 characters

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Next Steps (See SPEC.md)

- [ ] M1.3: Database client implementation
- [ ] M2: PDF extraction (Datalab, Azure, Gemini)
- [ ] M3: Comparison and validation pipeline
- [ ] M4: API endpoints implementation

## License

Internal project - DDT Dataset Generator Team
