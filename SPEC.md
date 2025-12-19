# SPEC - DDT Dataset Generator

## Task Breakdown

Questo documento contiene tutte le task atomiche per lo sviluppo del progetto.
Ogni task ha un ID univoco, dipendenze, e criteri di completamento.

---

## MILESTONE 1: Foundation & Database

### M1.1: Supabase Setup
**Owner:** db-architect
**Dependencies:** None
**Files:** N/A (Supabase Dashboard)

**Tasks:**
- [x] `M1.1.1` Creare progetto Supabase (se non esiste)
- [x] `M1.1.2` Eseguire SQL per tabella `dataset_samples`
- [x] `M1.1.3` Eseguire SQL per tabella `processing_stats`
- [x] `M1.1.4` Creare trigger `update_updated_at`
- [x] `M1.1.5` Creare bucket Storage `dataset-pdfs`
- [x] `M1.1.6` Configurare policy Storage (authenticated upload/read)
- [x] `M1.1.7` Testare insert manuale 1 record
- [x] `M1.1.8` Copiare credenziali in `.env`

**Done when:** Query `SELECT * FROM dataset_samples` funziona

---

### M1.2: Backend Skeleton
**Owner:** backend-developer
**Dependencies:** None
**Files:** `backend/`

**Tasks:**
- [x] `M1.2.1` Creare `backend/pyproject.toml` con dependencies:
  ```
  fastapi, uvicorn, python-dotenv, supabase, httpx,
  google-generativeai, azure-ai-formrecognizer, pydantic
  ```
- [x] `M1.2.2` Creare `backend/requirements.txt` (export da pyproject)
- [x] `M1.2.3` Creare `backend/src/__init__.py`
- [x] `M1.2.4` Creare `backend/src/config.py`:
  - Classe `Settings` con pydantic-settings
  - Load da environment variables
  - Validazione required fields
- [x] `M1.2.5` Creare `backend/src/main.py`:
  - FastAPI app instance
  - CORS middleware (allow localhost:3000)
  - Health check endpoint `GET /health`
- [x] `M1.2.6` Testare: `uvicorn src.main:app --reload`

**Done when:** `curl localhost:8000/health` returns `{"status": "ok"}`

---

### M1.3: Database Client
**Owner:** backend-developer
**Dependencies:** M1.1, M1.2
**Files:** `backend/src/database/`

**Tasks:**
- [x] `M1.3.1` Creare `backend/src/database/__init__.py`
- [x] `M1.3.2` Creare `backend/src/database/client.py`:
  - Singleton Supabase client
  - Funzioni: `get_client()`, `get_storage()`
- [x] `M1.3.3` Creare `backend/src/database/models.py`:
  - Pydantic model `DatasetSample` (matching DB schema)
  - Pydantic model `ProcessingStats`
  - Enum `SampleStatus`
- [x] `M1.3.4` Creare `backend/src/database/repository.py`:
  - `create_sample(filename, pdf_path) -> DatasetSample`
  - `get_sample(id) -> DatasetSample`
  - `get_samples(status?, limit?, offset?) -> list[DatasetSample]`
  - `update_sample(id, **fields) -> DatasetSample`
  - `get_stats() -> ProcessingStats`
  - `update_stats(**fields) -> ProcessingStats`
- [x] `M1.3.5` Test: insert + read sample funziona

**Done when:** Unit test `test_database.py` passa

---

## MILESTONE 2: Extractors

### M2.1: Datalab Extractor
**Owner:** backend-developer
**Dependencies:** M1.2
**Files:** `backend/src/extractors/datalab.py`

**Tasks:**
- [x] `M2.1.1` Creare `backend/src/extractors/__init__.py`
- [x] `M2.1.2` Creare `backend/src/extractors/schemas.py`:
  - `DDT_EXTRACTION_SCHEMA` (JSON string dal PRD)
  - `DDTOutput` Pydantic model
- [x] `M2.1.3` Creare `backend/src/extractors/datalab.py`:
  - Classe `DatalabExtractor`
  - Method `async extract(pdf_bytes: bytes) -> DatalabResult`
  - Implementare submit → poll loop
  - Poll interval: 3 seconds
  - Max polls: 100
  - Return: `DatalabResult(raw_ocr, extracted_json, processing_time_ms)`
- [x] `M2.1.4` Rate limiting: max 10 req/min
- [x] `M2.1.5` Error handling: timeout, API errors, invalid response
- [x] `M2.1.6` Test con 1 PDF reale da `samples/`

**Done when:** `test_datalab_extractor.py` passa con PDF reale

---

### M2.2: Azure OCR Extractor
**Owner:** backend-developer
**Dependencies:** M1.2
**Files:** `backend/src/extractors/azure_ocr.py`

**Tasks:**
- [x] `M2.2.1` Creare `backend/src/extractors/azure_ocr.py`:
  - Classe `AzureOCRExtractor`
  - Method `async extract(pdf_bytes: bytes) -> AzureOCRResult`
  - Usare `DocumentAnalysisClient` con model `prebuilt-read`
  - Return: `AzureOCRResult(raw_text, processing_time_ms)`
- [x] `M2.2.2` Rate limiting: max 1 req/sec
- [x] `M2.2.3` Error handling: 429, timeout, invalid PDF
- [x] `M2.2.4` Test con 1 PDF reale

**Done when:** `test_azure_ocr.py` passa con PDF reale

---

### M2.3: Gemini Extractor
**Owner:** backend-developer
**Dependencies:** M2.2
**Files:** `backend/src/extractors/gemini.py`

**Tasks:**
- [x] `M2.3.1` Creare `backend/src/extractors/gemini.py`:
  - Classe `GeminiExtractor`
  - Method `async extract(ocr_text: str) -> GeminiResult`
  - System prompt + user prompt dal PRD
  - JSON mode con schema
  - Return: `GeminiResult(extracted_json, processing_time_ms)`
- [x] `M2.3.2` Rate limiting: max 10 req/min
- [x] `M2.3.3` Retry su JSON parse error (max 2 retry)
- [x] `M2.3.4` Error handling: rate limit, invalid response
- [x] `M2.3.5` Test con OCR output reale

**Done when:** `test_gemini_extractor.py` passa

---

## MILESTONE 3: Processing Pipeline

### M3.1: Comparison Logic
**Owner:** backend-developer
**Dependencies:** M2.1, M2.2, M2.3
**Files:** `backend/src/processing/comparison.py`

**Tasks:**
- [x] `M3.1.1` Creare `backend/src/processing/__init__.py`
- [x] `M3.1.2` Creare `backend/src/processing/comparison.py`:
  - Function `normalize(value: str | None) -> str | None`
  - Function `values_match(val1, val2) -> bool` (con fuzzy 0.85)
  - Function `calculate_match_score(datalab, gemini) -> tuple[float, list[str]]`
- [x] `M3.1.3` Unit tests per tutti i casi edge:
  - Both null → match
  - One null → no match
  - Exact match → match
  - Fuzzy match (>0.85) → match
  - Different values → no match
- [x] `M3.1.4` Test con 5 scenari realistici

**Done when:** `test_comparison.py` passa con 100% coverage

---

### M3.2: Processing Pipeline
**Owner:** backend-developer
**Dependencies:** M3.1, M1.3
**Files:** `backend/src/processing/pipeline.py`

**Tasks:**
- [x] `M3.2.1` Creare `backend/src/processing/pipeline.py`:
  - Classe `ProcessingPipeline`
  - Method `async process_single(sample_id: str) -> ProcessingResult`
    1. Fetch PDF from storage
    2. Run Datalab extraction
    3. Run Azure OCR
    4. Run Gemini extraction on Azure OCR
    5. Calculate match score
    6. Determine status (auto_validated if >= 0.95)
    7. Update sample in DB
  - Method `async process_all_pending() -> ProcessingSummary`
    - Get all pending samples
    - Process with max 2 parallel
    - Update stats after each
- [x] `M3.2.2` Concurrency control: semaphore max 2
- [x] `M3.2.3` Progress tracking: update `processing_stats` table
- [x] `M3.2.4` Error handling: mark sample as "error", continue batch
- [x] `M3.2.5` Test con 3 PDF

**Done when:** `test_pipeline.py` passa, 3 samples processati correttamente

---

### M3.3: Alpaca Formatter
**Owner:** backend-developer
**Dependencies:** M1.3
**Files:** `backend/src/processing/alpaca_formatter.py`

**Tasks:**
- [x] `M3.3.1` Creare `backend/src/processing/alpaca_formatter.py`:
  - Function `format_to_alpaca(sample, ocr_source) -> dict`
  - Function `export_dataset(samples, ocr_source) -> tuple[str, str]`
    - Split train/validation (93%/7%)
    - Return (training_jsonl, validation_jsonl)
  - Function `generate_quality_report(samples) -> dict`
- [x] `M3.3.2` Validare output JSONL è parsabile
- [x] `M3.3.3` Test export con 10 mock samples

**Done when:** `test_alpaca_formatter.py` passa, JSONL valido

---

## MILESTONE 4: API Endpoints

### M4.1: API Schemas
**Owner:** backend-developer
**Dependencies:** M1.3
**Files:** `backend/src/api/schemas.py`

**Tasks:**
- [ ] `M4.1.1` Creare `backend/src/api/__init__.py`
- [ ] `M4.1.2` Creare `backend/src/api/schemas.py`:
  - `UploadResponse`
  - `ProcessResponse`
  - `StatusResponse`
  - `SampleListResponse`
  - `SampleDetailResponse`
  - `ValidationRequest`
  - `ValidationResponse`
  - `ExportRequest`
  - `ExportResponse`

**Done when:** Tutti gli schema definiti, importabili

---

### M4.2: API Routes
**Owner:** backend-developer
**Dependencies:** M4.1, M3.2, M3.3
**Files:** `backend/src/api/routes.py`

**Tasks:**
- [ ] `M4.2.1` Creare `backend/src/api/routes.py`:
  - `POST /api/upload` - upload PDF
  - `POST /api/process` - start processing
  - `GET /api/status` - processing status
  - `GET /api/samples` - list samples
  - `GET /api/samples/{id}` - sample detail
  - `PATCH /api/samples/{id}` - manual validation
  - `POST /api/export` - generate dataset
- [ ] `M4.2.2` Background task per processing
- [ ] `M4.2.3` File upload to Supabase Storage
- [ ] `M4.2.4` Signed URL per PDF download
- [ ] `M4.2.5` Export genera file e ritorna URL
- [ ] `M4.2.6` Includere router in `main.py`
- [ ] `M4.2.7` Test tutti endpoint con curl/httpie

**Done when:** OpenAPI docs completa, tutti endpoint funzionano

---

## MILESTONE 5: Frontend

### M5.1: Frontend Setup
**Owner:** frontend-developer
**Dependencies:** None
**Files:** `frontend/`

**Tasks:**
- [ ] `M5.1.1` `npx create-next-app@latest frontend --typescript --tailwind --app`
- [ ] `M5.1.2` `npx shadcn@latest init`
- [ ] `M5.1.3` Installare componenti shadcn:
  ```
  button, card, table, dialog, progress, toast,
  input, label, badge, tabs, separator
  ```
- [ ] `M5.1.4` `npm install @tanstack/react-query react-dropzone`
- [ ] `M5.1.5` Creare `frontend/src/lib/api.ts`:
  - API client con fetch
  - Tutte le chiamate backend
- [ ] `M5.1.6` Creare `frontend/src/lib/utils.ts`
- [ ] `M5.1.7` Setup React Query provider in layout
- [ ] `M5.1.8` Test: `npm run dev` funziona

**Done when:** App Next.js parte senza errori

---

### M5.2: Home Page (Upload + Status)
**Owner:** frontend-developer
**Dependencies:** M5.1, M4.2
**Files:** `frontend/src/app/page.tsx`, `frontend/src/components/`

**Tasks:**
- [ ] `M5.2.1` Creare `components/upload-zone.tsx`:
  - Drag & drop con react-dropzone
  - Accept only PDF
  - Multiple files
  - Upload progress
  - Call POST /api/upload per ogni file
- [ ] `M5.2.2` Creare `components/processing-status.tsx`:
  - Polling GET /api/status ogni 2s quando processing
  - Progress bar
  - Stats cards (auto/review/errors)
  - Start processing button
- [ ] `M5.2.3` Creare `components/samples-table.tsx`:
  - Lista samples con status badge
  - Sort by status, date
  - Click → go to review
- [ ] `M5.2.4` Assemblare in `app/page.tsx`
- [ ] `M5.2.5` Test: upload 3 PDF, vedere status

**Done when:** Upload funziona, status si aggiorna

---

### M5.3: Review Page
**Owner:** frontend-developer
**Dependencies:** M5.1, M4.2
**Files:** `frontend/src/app/review/page.tsx`

**Tasks:**
- [ ] `M5.3.1` Creare `components/pdf-viewer.tsx`:
  - Embed PDF con `<iframe>` o `<object>`
  - Zoom controls
- [ ] `M5.3.2` Creare `components/comparison-table.tsx`:
  - Side-by-side Datalab vs Gemini
  - Highlight discrepancies (red background)
  - Show match/mismatch icon per campo
- [ ] `M5.3.3` Creare `components/validation-actions.tsx`:
  - Button: Accept Datalab
  - Button: Accept Gemini
  - Button: Edit Manual (opens modal)
  - Button: Reject
  - Textarea: notes
- [ ] `M5.3.4` Creare `components/edit-modal.tsx`:
  - Form con tutti i campi DDT
  - Pre-fill con Datalab o Gemini
  - Save → PATCH /api/samples/{id}
- [ ] `M5.3.5` Creare `app/review/page.tsx`:
  - Query param `?id=xxx` per sample specifico
  - Oppure lista filtrata needs_review
  - Navigation: Previous/Next
- [ ] `M5.3.6` Test: validare 2 samples manualmente

**Done when:** Validation flow completo funziona

---

### M5.4: Export Page
**Owner:** frontend-developer
**Dependencies:** M5.1, M4.2
**Files:** `frontend/src/app/export/page.tsx`

**Tasks:**
- [ ] `M5.4.1` Creare `components/export-summary.tsx`:
  - Stats totali dataset
  - Breakdown per status
- [ ] `M5.4.2` Creare `components/export-settings.tsx`:
  - Radio: OCR source (azure/datalab)
  - Slider: validation split %
- [ ] `M5.4.3` Creare `components/quality-report.tsx`:
  - Display quality metrics
  - Field coverage chart (optional)
- [ ] `M5.4.4` Creare `app/export/page.tsx`:
  - Summary
  - Settings
  - Download buttons
  - Quality report modal
- [ ] `M5.4.5` Test: export dataset, download files

**Done when:** Export genera JSONL validi, download funziona

---

## MILESTONE 6: Integration & Polish

### M6.1: Docker Setup
**Owner:** devops
**Dependencies:** M4.2, M5.4
**Files:** `docker-compose.yml`, `*/Dockerfile`

**Tasks:**
- [ ] `M6.1.1` Creare `backend/Dockerfile`:
  - Python 3.11 slim
  - Install dependencies
  - Run uvicorn
- [ ] `M6.1.2` Creare `frontend/Dockerfile`:
  - Node 20 alpine
  - Build Next.js
  - Run with next start
- [ ] `M6.1.3` Creare `docker-compose.yml`:
  - Backend service (port 8000)
  - Frontend service (port 3000)
  - Environment from .env
- [ ] `M6.1.4` Test: `docker-compose up` funziona

**Done when:** `docker-compose up` avvia entrambi i servizi

---

### M6.2: End-to-End Test
**Owner:** test-engineer
**Dependencies:** M6.1
**Files:** `backend/tests/test_e2e.py`

**Tasks:**
- [ ] `M6.2.1` Creare test E2E:
  1. Upload 5 PDF
  2. Start processing
  3. Wait completion
  4. Verify status distribution
  5. Manual validate 1 sample
  6. Export dataset
  7. Validate JSONL format
  8. Check quality report
- [ ] `M6.2.2` Run test con Docker

**Done when:** E2E test passa

---

### M6.3: Documentation
**Owner:** Any
**Dependencies:** M6.2
**Files:** `README.md`

**Tasks:**
- [ ] `M6.3.1` Scrivere README.md:
  - Quick start
  - Prerequisites
  - Setup instructions
  - Usage guide
  - API reference link
- [ ] `M6.3.2` Aggiungere screenshots UI

**Done when:** README permette setup da zero

---

## Summary

| Milestone | Tasks | Est. Effort |
|-----------|-------|-------------|
| M1: Foundation | 8 | Day 1 |
| M2: Extractors | 6 | Day 2-3 |
| M3: Pipeline | 5 | Day 4 |
| M4: API | 7 | Day 5 |
| M5: Frontend | 15 | Day 6-8 |
| M6: Polish | 5 | Day 9-10 |
| **Total** | **46 tasks** | **~10 days** |

---

## Task Status Legend

- [ ] `Pending` - Not started
- [x] `Done` - Completed and tested
- [~] `In Progress` - Currently working
- [!] `Blocked` - Waiting on dependency
