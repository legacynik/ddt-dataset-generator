# DDT Dataset Generator - Technical Specification

## Vision

Piattaforma per creare dataset di training per l'estrazione dati da DDT italiani, con:
1. **Playground** per testare diversi LLM extractors
2. **Benchmarking** per identificare il migliore
3. **Dataset generation** con l'extractor vincente
4. **Fine-tuning** di small LLM specializzati
5. **Confronto** tra small LLM fine-tuned vs LLM potenti

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           COMPLETE PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────┐      ┌─────────────────────────────────────────────────┐  │
│   │   PDF   │─────►│  OCR LAYER (run once, cached)                   │  │
│   └─────────┘      │  ├─ Azure Document Intelligence → raw_text      │  │
│                    │  └─ Datalab Marker → raw_text + structured      │  │
│                    └─────────────────────────────────────────────────┘  │
│                                        │                                 │
│                                        ▼                                 │
│                    ┌─────────────────────────────────────────────────┐  │
│                    │  EXTRACTION LAYER (configurable, parallel)      │  │
│                    │  ┌─────────────────────────────────────────┐    │  │
│                    │  │  Extractor 1: Datalab (baseline)        │    │  │
│                    │  │  Extractor 2: Gemini 1.5 Flash          │    │  │
│                    │  │  Extractor 3: Claude 3.5 Sonnet (OR)    │    │  │
│                    │  │  Extractor 4: GPT-4o (OpenRouter)       │    │  │
│                    │  │  Extractor 5: Llama 3.1 70B (Ollama)    │    │  │
│                    │  │  Extractor N: Custom fine-tuned model   │    │  │
│                    │  └─────────────────────────────────────────┘    │  │
│                    └─────────────────────────────────────────────────┘  │
│                                        │                                 │
│                                        ▼                                 │
│                    ┌─────────────────────────────────────────────────┐  │
│                    │  VALIDATION LAYER                               │  │
│                    │  ├─ Manual validation (ground truth)            │  │
│                    │  ├─ Cross-validation (consensus)                │  │
│                    │  └─ Auto-validation (when extractors agree)     │  │
│                    └─────────────────────────────────────────────────┘  │
│                                        │                                 │
│                                        ▼                                 │
│                    ┌─────────────────────────────────────────────────┐  │
│                    │  OUTPUT                                         │  │
│                    │  └─ Alpaca JSONL Dataset (train + validation)   │  │
│                    └─────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Workflow

### Phase 1: OCR (One-Time)
```
1. Upload PDFs
2. Run Azure OCR → cache raw_text
3. Run Datalab → cache raw_text + structured extraction
4. Store in dataset_samples (permanent)
```

### Phase 2: Playground Testing
```
1. Configure multiple extractors (Gemini, Claude, GPT-4, etc.)
2. Run test batch (15-20 DDTs) with each extractor
3. Manually validate a subset → ground truth
4. Calculate accuracy per extractor
5. Identify winning extractor
```

### Phase 3: Dataset Generation
```
1. Use winning extractor on full corpus
2. Auto-validate where confidence is high
3. Manual review for edge cases
4. Export Alpaca JSONL dataset
```

### Phase 4: Fine-Tuning (Future)
```
1. Fine-tune small LLM (Llama 3.1 8B, Qwen 2.5, etc.)
2. Add fine-tuned model as new extractor
3. Benchmark vs powerful LLMs on new DDTs
4. Iterate until small model matches/beats large models
```

---

## Database Schema

### Core Tables (Existing, Modified)

```sql
-- ===========================================
-- TABLE: dataset_samples (MODIFIED)
-- ===========================================
-- Stores PDF metadata and CACHED OCR results (never re-run)
CREATE TABLE dataset_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- File info
    filename VARCHAR(255) NOT NULL,
    pdf_storage_path TEXT NOT NULL,
    file_size_bytes INTEGER,

    -- CACHED OCR (run once, permanent)
    azure_raw_ocr TEXT,                    -- Azure OCR text (cached)
    azure_processing_time_ms INTEGER,
    datalab_raw_ocr TEXT,                  -- Datalab OCR text (cached)
    datalab_structured JSONB,              -- Datalab structured extraction (baseline)
    datalab_processing_time_ms INTEGER,
    ocr_completed_at TIMESTAMPTZ,          -- When OCR was cached

    -- Ground truth (from manual validation)
    ground_truth_json JSONB,               -- Manually verified correct values
    ground_truth_validated_at TIMESTAMPTZ,
    ground_truth_notes TEXT,

    -- Dataset assignment
    dataset_split VARCHAR(10) CHECK (dataset_split IN ('train', 'validation', 'test'))
);
```

### New Tables

```sql
-- ===========================================
-- TABLE: extractors
-- ===========================================
-- Configurable extraction models
CREATE TABLE extractors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Identity
    name VARCHAR(100) NOT NULL UNIQUE,     -- "Gemini 1.5 Flash", "Claude 3.5 Sonnet"
    description TEXT,

    -- Type and model
    type VARCHAR(20) NOT NULL              -- gemini, openrouter, ollama, datalab, custom
        CHECK (type IN ('gemini', 'openrouter', 'ollama', 'datalab', 'custom')),
    model_id VARCHAR(100) NOT NULL,        -- "gemini-1.5-flash", "anthropic/claude-3.5-sonnet"

    -- Configuration
    system_prompt TEXT NOT NULL,
    extraction_schema JSONB NOT NULL,      -- JSON schema for extraction
    temperature DECIMAL(3,2) DEFAULT 0.1,
    max_tokens INTEGER DEFAULT 2048,

    -- API settings
    api_base_url TEXT,                     -- For OpenRouter/Ollama
    api_key_env VARCHAR(50),               -- Env var name: "OPENROUTER_API_KEY"

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_baseline BOOLEAN DEFAULT FALSE,     -- Mark one as baseline for comparison

    -- Calculated accuracy (updated after benchmarks)
    overall_accuracy DECIMAL(5,4),         -- 0.0000 to 1.0000
    last_benchmark_at TIMESTAMPTZ
);

-- ===========================================
-- TABLE: extraction_runs
-- ===========================================
-- Test runs for benchmarking extractors
CREATE TABLE extraction_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMPTZ,

    -- Identity
    name VARCHAR(100) NOT NULL,            -- "Test Run 2024-12-19 #1"
    description TEXT,

    -- Configuration
    extractor_id UUID NOT NULL REFERENCES extractors(id),

    -- Scope
    sample_ids UUID[],                     -- Specific samples, or NULL for all

    -- Status
    status VARCHAR(20) DEFAULT 'pending' NOT NULL
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

    -- Aggregated results
    total_samples INTEGER DEFAULT 0,
    processed INTEGER DEFAULT 0,
    successful INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,

    -- Accuracy (calculated vs ground truth where available)
    accuracy_vs_ground_truth DECIMAL(5,4),
    accuracy_vs_baseline DECIMAL(5,4),     -- vs Datalab
    avg_processing_time_ms INTEGER,

    -- Notes
    notes TEXT
);

-- ===========================================
-- TABLE: extraction_results
-- ===========================================
-- Results per sample per run
CREATE TABLE extraction_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Links
    run_id UUID NOT NULL REFERENCES extraction_runs(id) ON DELETE CASCADE,
    sample_id UUID NOT NULL REFERENCES dataset_samples(id) ON DELETE CASCADE,
    extractor_id UUID NOT NULL REFERENCES extractors(id),

    -- Results
    extracted_json JSONB,
    processing_time_ms INTEGER,
    error_message TEXT,
    success BOOLEAN DEFAULT TRUE,

    -- Comparison scores
    match_vs_ground_truth DECIMAL(5,4),    -- vs manual validation
    match_vs_baseline DECIMAL(5,4),        -- vs Datalab
    field_matches JSONB,                   -- {"mittente": true, "numero_documento": false, ...}

    UNIQUE(run_id, sample_id)
);

-- ===========================================
-- TABLE: field_accuracy
-- ===========================================
-- Per-field accuracy tracking for each extractor
CREATE TABLE field_accuracy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    extractor_id UUID NOT NULL REFERENCES extractors(id) ON DELETE CASCADE,
    field_name VARCHAR(50) NOT NULL,       -- "mittente", "numero_documento", etc.

    correct_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    accuracy DECIMAL(5,4),                 -- correct_count / total_count

    UNIQUE(extractor_id, field_name)
);

-- Indexes
CREATE INDEX idx_extraction_results_run ON extraction_results(run_id);
CREATE INDEX idx_extraction_results_sample ON extraction_results(sample_id);
CREATE INDEX idx_extraction_results_extractor ON extraction_results(extractor_id);
CREATE INDEX idx_extraction_runs_extractor ON extraction_runs(extractor_id);
CREATE INDEX idx_field_accuracy_extractor ON field_accuracy(extractor_id);
```

---

## API Endpoints

### Extractors Management

```
GET    /api/extractors                     List all extractors
POST   /api/extractors                     Create new extractor
GET    /api/extractors/{id}                Get extractor details
PATCH  /api/extractors/{id}                Update extractor config
DELETE /api/extractors/{id}                Delete extractor
POST   /api/extractors/{id}/test           Test extractor on single sample
POST   /api/extractors/{id}/set-baseline   Set as baseline for comparison
```

### Extraction Runs

```
GET    /api/runs                           List all runs
POST   /api/runs                           Create and start new run
GET    /api/runs/{id}                      Get run details
GET    /api/runs/{id}/results              Get detailed results
DELETE /api/runs/{id}                      Delete run
POST   /api/runs/{id}/cancel               Cancel running extraction
```

### Comparison & Benchmarking

```
GET    /api/benchmark                      Get extractor leaderboard
GET    /api/benchmark/compare?ids=a,b      Compare two extractors
GET    /api/samples/{id}/extractions       Get all extractions for sample
POST   /api/samples/{id}/ground-truth      Set ground truth for sample
```

### Dataset Export

```
POST   /api/export                         Export dataset
       - extractor_id: which extractor's output to use
       - ocr_source: "azure" or "datalab"
       - split_ratio: train/validation split
```

---

## Extractor Types

### 1. Gemini (Native)
```python
{
    "type": "gemini",
    "model_id": "gemini-1.5-flash",  # or gemini-1.5-pro
    "api_key_env": "GOOGLE_API_KEY"
}
```

### 2. OpenRouter (Multi-Model)
```python
{
    "type": "openrouter",
    "model_id": "anthropic/claude-3.5-sonnet",  # or openai/gpt-4o, meta-llama/llama-3.1-70b
    "api_base_url": "https://openrouter.ai/api/v1",
    "api_key_env": "OPENROUTER_API_KEY"
}
```

### 3. Ollama (Local)
```python
{
    "type": "ollama",
    "model_id": "llama3.1:8b",  # or mistral, qwen2.5, etc.
    "api_base_url": "http://localhost:11434"
}
```

### 4. Datalab (Baseline)
```python
{
    "type": "datalab",
    "model_id": "datalab-marker",
    "is_baseline": True  # Always compare against this
}
```

### 5. Custom (Fine-tuned)
```python
{
    "type": "custom",
    "model_id": "ddt-extractor-v1",  # Your fine-tuned model
    "api_base_url": "http://your-model-server:8080"
}
```

---

## Dashboard UI

### 1. Playground Page (`/playground`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Extraction Playground                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Extractors                                              [+ Add] │    │
│  │  ───────────────────────────────────────────────────────────── │    │
│  │  ● Datalab (baseline)              85.2%    ✓ Active           │    │
│  │  ○ Gemini 1.5 Flash                91.4%    ✓ Active           │    │
│  │  ○ Claude 3.5 Sonnet (OpenRouter)  94.1%    ✓ Active           │    │
│  │  ○ GPT-4o (OpenRouter)             92.8%    ✓ Active           │    │
│  │  ○ Llama 3.1 70B (Ollama)          88.5%    ○ Inactive         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Selected: Claude 3.5 Sonnet                          [Edit]    │    │
│  │  ─────────────────────────────────────────────────────────────  │    │
│  │                                                                  │    │
│  │  System Prompt:                                                  │    │
│  │  ┌─────────────────────────────────────────────────────────┐   │    │
│  │  │ Sei un assistente specializzato nell'estrazione dati   │   │    │
│  │  │ da Documenti di Trasporto (DDT) italiani.              │   │    │
│  │  │                                                         │   │    │
│  │  │ REGOLE:                                                 │   │    │
│  │  │ 1. Estrai SOLO i dati richiesti...                     │   │    │
│  │  └─────────────────────────────────────────────────────────┘   │    │
│  │                                                                  │    │
│  │  Temperature: [0.1] ────●───────────────                        │    │
│  │                                                                  │    │
│  │  Extraction Schema:                                              │    │
│  │  ┌─────────────────────────────────────────────────────────┐   │    │
│  │  │ {                                                       │   │    │
│  │  │   "properties": {                                       │   │    │
│  │  │     "mittente": {"description": "Ragione sociale..."}  │   │    │
│  │  │   }                                                     │   │    │
│  │  │ }                                                       │   │    │
│  │  └─────────────────────────────────────────────────────────┘   │    │
│  │                                                                  │    │
│  │  [Save Changes]   [Test on 1 Sample]   [Start Test Run (20)]   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. Benchmark Page (`/benchmark`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Extractor Benchmark                                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🏆 LEADERBOARD (vs Ground Truth on 20 samples)                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  #   Extractor              Accuracy   Avg Time   Cost/1K      │    │
│  │  ───────────────────────────────────────────────────────────── │    │
│  │  1.  Claude 3.5 Sonnet      94.1%      2.1s       $0.015       │    │
│  │  2.  GPT-4o                 92.8%      1.8s       $0.025       │    │
│  │  3.  Gemini 1.5 Flash       91.4%      1.5s       $0.001       │    │
│  │  4.  Llama 3.1 70B          88.5%      3.2s       $0.000       │    │
│  │  5.  Datalab (baseline)     85.2%      120s       $0.050       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  📊 FIELD-LEVEL ACCURACY                                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Field                 Claude   GPT-4o   Gemini   Datalab      │    │
│  │  ───────────────────────────────────────────────────────────── │    │
│  │  mittente              95%      94%      92%      88%          │    │
│  │  destinatario          96%      95%      93%      87%          │    │
│  │  indirizzo_dest        92%      90%      88%      82%          │    │
│  │  data_documento        98%      98%      97%      95%          │    │
│  │  numero_documento      95%      94%      92%      85%          │    │
│  │  numero_ordine         88%      85%      82%      75%          │    │
│  │  codice_cliente        90%      88%      85%      80%          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  [Use "Claude 3.5 Sonnet" for Dataset Generation]                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3. Runs History (`/runs`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Test Runs                                                   [+ New Run]│
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Run Name              Extractor        Samples  Accuracy  Time │    │
│  │  ───────────────────────────────────────────────────────────── │    │
│  │  Test #5 - Claude      Claude 3.5       20       94.1%     42s │    │
│  │  Test #4 - GPT-4       GPT-4o           20       92.8%     36s │    │
│  │  Test #3 - Gemini      Gemini Flash     20       91.4%     30s │    │
│  │  Test #2 - Llama       Llama 3.1 70B    20       88.5%     64s │    │
│  │  Test #1 - Baseline    Datalab          20       85.2%     40m │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  [Compare Selected]  [Delete Selected]                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4. Sample Detail (with extraction history)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Sample: doc001.pdf                                              [PDF]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📋 GROUND TRUTH (manually validated)                    [Edit]         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  mittente: DENSO THERMAL SYSTEMS S.P.A.                         │    │
│  │  destinatario: RHIAG INTER AUTO PARTS ITALIA SRL                │    │
│  │  numero_documento: 77070609                                      │    │
│  │  ...                                                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  📊 EXTRACTION RESULTS                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Extractor        mittente    destinatario    num_doc   Score  │    │
│  │  ───────────────────────────────────────────────────────────── │    │
│  │  Claude 3.5       ✓           ✓               ✓         100%   │    │
│  │  GPT-4o           ✓           ✓               ✓         100%   │    │
│  │  Gemini           ✓           ✗ (RHIAG SPA)   ✓         87.5%  │    │
│  │  Datalab          ✓           ✓               ✗ (7707)  87.5%  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  [View Full Comparison]                                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation
1. ✅ OCR caching (already implemented in dataset_samples)
2. Create `extractors` table and seed defaults
3. Create `extraction_runs` and `extraction_results` tables
4. Add `ground_truth_json` to dataset_samples

### Phase 2: Multi-Extractor Support
1. Implement OpenRouter extractor class
2. Implement Ollama extractor class
3. Create extractor factory/registry
4. API endpoints for extractor management

### Phase 3: Run Management
1. API endpoints for runs
2. Run execution engine (parallel extraction)
3. Accuracy calculation vs ground truth
4. Field-level accuracy tracking

### Phase 4: Dashboard UI
1. Playground page (extractor config editor)
2. Benchmark page (leaderboard)
3. Runs history page
4. Sample detail with extraction history

### Phase 5: Dataset Generation
1. Export using selected extractor
2. Confidence-based auto-validation
3. Quality report generation

### Phase 6: Fine-Tuning Integration (Future)
1. Add "custom" extractor type
2. Integration with fine-tuning platforms
3. A/B testing fine-tuned vs base models

---

## Environment Variables

```bash
# Existing
GOOGLE_API_KEY=...           # Gemini
AZURE_ENDPOINT=...           # Azure OCR
AZURE_API_KEY=...            # Azure OCR
DATALAB_API_KEY=...          # Datalab

# New
OPENROUTER_API_KEY=...       # OpenRouter (Claude, GPT-4, Llama, etc.)
OLLAMA_BASE_URL=http://localhost:11434  # Local Ollama
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Find best extractor | <5 test runs |
| Ground truth validation | 15-20 samples |
| Auto-validation accuracy | >95% |
| Dataset quality score | >90% field coverage |
| Fine-tuned model parity | Match best LLM accuracy |
