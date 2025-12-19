# DDT Dataset Generator - Technical Specification

## Feature: Extraction Pipeline Playground

### Overview

Sistema di A/B testing per ottimizzare la pipeline di estrazione OCR. Permette di:
- Modificare prompt e schema di estrazione dalla dashboard
- Eseguire "test run" con configurazioni diverse
- Confrontare risultati tra run differenti
- Identificare la configurazione ottimale per massimizzare il match score

---

## Architecture

### New Database Schema

```sql
-- ===========================================
-- TABLE: extraction_configs
-- ===========================================
-- Stores different prompt/schema configurations
CREATE TABLE extraction_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    name VARCHAR(100) NOT NULL,              -- "Baseline v1", "Test prompt italiano", etc.
    description TEXT,

    -- Gemini configuration
    gemini_system_prompt TEXT NOT NULL,
    gemini_temperature DECIMAL(3,2) DEFAULT 0.1,

    -- Datalab configuration
    datalab_schema JSONB NOT NULL,           -- DDT_EXTRACTION_SCHEMA

    -- Metadata
    is_default BOOLEAN DEFAULT FALSE,        -- Mark the production config
    created_by VARCHAR(100) DEFAULT 'system'
);

-- ===========================================
-- TABLE: processing_runs
-- ===========================================
-- Tracks each test/processing run
CREATE TABLE processing_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMPTZ,

    name VARCHAR(100) NOT NULL,              -- "Test Run 2024-12-19 #1"
    description TEXT,

    -- Configuration used
    config_id UUID REFERENCES extraction_configs(id),

    -- Status
    status VARCHAR(20) DEFAULT 'pending' NOT NULL
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),

    -- Aggregated results
    total_samples INTEGER DEFAULT 0,
    processed INTEGER DEFAULT 0,
    auto_validated INTEGER DEFAULT 0,
    needs_review INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    avg_match_score DECIMAL(5,4),
    total_processing_time_ms BIGINT,

    -- Notes
    notes TEXT
);

-- ===========================================
-- TABLE: run_results
-- ===========================================
-- Stores extraction results per run (allows multiple runs per sample)
CREATE TABLE run_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Links
    run_id UUID NOT NULL REFERENCES processing_runs(id) ON DELETE CASCADE,
    sample_id UUID NOT NULL REFERENCES dataset_samples(id) ON DELETE CASCADE,

    -- Datalab results
    datalab_raw_ocr TEXT,
    datalab_json JSONB,
    datalab_processing_time_ms INTEGER,
    datalab_error TEXT,

    -- Azure + Gemini results
    azure_raw_ocr TEXT,
    azure_processing_time_ms INTEGER,
    azure_error TEXT,
    gemini_json JSONB,
    gemini_processing_time_ms INTEGER,
    gemini_error TEXT,

    -- Comparison
    match_score DECIMAL(5,4),
    discrepancies TEXT[],

    -- Validation
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    validated_output JSONB,

    UNIQUE(run_id, sample_id)  -- One result per sample per run
);

-- Indexes
CREATE INDEX idx_run_results_run_id ON run_results(run_id);
CREATE INDEX idx_run_results_sample_id ON run_results(sample_id);
CREATE INDEX idx_run_results_match_score ON run_results(match_score);
```

---

## API Endpoints

### Configuration Management

```
GET    /api/configs                    List all extraction configs
POST   /api/configs                    Create new config
GET    /api/configs/{id}               Get config details
PATCH  /api/configs/{id}               Update config
DELETE /api/configs/{id}               Delete config (if not used)
POST   /api/configs/{id}/set-default   Set as default config
```

### Run Management

```
GET    /api/runs                       List all runs
POST   /api/runs                       Create and start new run
GET    /api/runs/{id}                  Get run details + results
DELETE /api/runs/{id}                  Delete run and its results
GET    /api/runs/{id}/results          Get detailed results for run
```

### Comparison

```
GET    /api/runs/compare?run_ids=id1,id2    Compare two runs
GET    /api/samples/{id}/history            Get all run results for a sample
```

---

## API Schemas

### CreateConfigRequest
```json
{
  "name": "Test italiano v2",
  "description": "Prompt ottimizzato per DDT italiani",
  "gemini_system_prompt": "Sei un assistente specializzato...",
  "gemini_temperature": 0.1,
  "datalab_schema": {
    "type": "object",
    "properties": {
      "mittente": {"type": "string", "description": "..."},
      ...
    }
  }
}
```

### CreateRunRequest
```json
{
  "name": "Test Run #3",
  "description": "Testing new prompt",
  "config_id": "uuid-of-config",
  "sample_ids": null  // null = all samples, or list of specific IDs
}
```

### CompareRunsResponse
```json
{
  "runs": [
    {
      "id": "run-1-uuid",
      "name": "Baseline",
      "config_name": "Default v1",
      "avg_match_score": 0.82,
      "auto_validated": 6,
      "needs_review": 15
    },
    {
      "id": "run-2-uuid",
      "name": "New Prompt",
      "config_name": "Test italiano v2",
      "avg_match_score": 0.91,
      "auto_validated": 14,
      "needs_review": 7
    }
  ],
  "comparison": {
    "match_score_delta": +0.09,
    "auto_validated_delta": +8,
    "improved_samples": ["sample-1", "sample-5", ...],
    "degraded_samples": ["sample-12"],
    "field_improvements": {
      "mittente": {"run1_accuracy": 0.85, "run2_accuracy": 0.95},
      "numero_ordine": {"run1_accuracy": 0.70, "run2_accuracy": 0.88}
    }
  }
}
```

---

## Dashboard UI Components

### 1. Playground Page (`/playground`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Extraction Pipeline Playground                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │ Configurations      │  │ Gemini System Prompt            │  │
│  │ ─────────────────── │  │ ┌─────────────────────────────┐ │  │
│  │ ○ Default v1        │  │ │ Sei un assistente          │ │  │
│  │ ● Test italiano v2  │  │ │ specializzato...           │ │  │
│  │ ○ Minimal prompt    │  │ │                             │ │  │
│  │                     │  │ │ REGOLE:                     │ │  │
│  │ [+ New Config]      │  │ │ 1. Estrai SOLO...          │ │  │
│  └─────────────────────┘  │ └─────────────────────────────┘ │  │
│                           │                                  │  │
│                           │ Temperature: [0.1] ────○───────  │  │
│                           └─────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Datalab Extraction Schema (JSON)                          │  │
│  │ ┌──────────────────────────────────────────────────────┐ │  │
│  │ │ {                                                     │ │  │
│  │ │   "properties": {                                     │ │  │
│  │ │     "mittente": {                                     │ │  │
│  │ │       "description": "Estrai SOLO la Ragione..."     │ │  │
│  │ │     },                                                │ │  │
│  │ │     ...                                               │ │  │
│  │ │   }                                                   │ │  │
│  │ │ }                                                     │ │  │
│  │ └──────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌─────────────────┐                       │
│  │ 💾 Save Config │  │ ▶ Start Test Run │                       │
│  └────────────────┘  └─────────────────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Runs Comparison Page (`/runs`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Test Runs                                              [+ New] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ □ Run Name          Config        Score  Auto  Review   │   │
│  │ ─────────────────────────────────────────────────────── │   │
│  │ ☑ Baseline v1       Default       82%    6     15      │   │
│  │ ☑ Test italiano     Test v2       91%    14    7       │   │
│  │ □ Minimal prompt    Minimal       75%    4     17      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [Compare Selected]                                             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Comparison: Baseline v1 vs Test italiano                       │
│  ─────────────────────────────────────────                      │
│                                                                  │
│  Match Score:     82% → 91%  (+9% ✓)                           │
│  Auto-validated:  6 → 14     (+8 ✓)                            │
│  Needs Review:    15 → 7     (-8 ✓)                            │
│                                                                  │
│  Field Accuracy Improvements:                                   │
│  ┌────────────────────┬──────────┬──────────┬─────────┐        │
│  │ Field              │ Run 1    │ Run 2    │ Delta   │        │
│  ├────────────────────┼──────────┼──────────┼─────────┤        │
│  │ mittente           │ 85%      │ 95%      │ +10% ✓  │        │
│  │ numero_ordine      │ 70%      │ 88%      │ +18% ✓  │        │
│  │ codice_cliente     │ 60%      │ 75%      │ +15% ✓  │        │
│  └────────────────────┴──────────┴──────────┴─────────┘        │
│                                                                  │
│  [Set "Test italiano" as Default]                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Sample History View (in Sample Detail)

```
┌─────────────────────────────────────────────────────────────────┐
│  Sample: doc001.pdf                                             │
├─────────────────────────────────────────────────────────────────┤
│  Run History:                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Run              Score   mittente        numero_doc     │   │
│  │ ──────────────────────────────────────────────────────  │   │
│  │ Baseline v1      75%     LAVAZZA ✓       DDT-123 ✗     │   │
│  │ Test italiano    100%    LAVAZZA ✓       8797 ✓        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [View Diff] [Use Result from "Test italiano"]                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Database & Core API
1. Create new database tables
2. Migrate existing results to a "Baseline" run
3. Implement config CRUD endpoints
4. Implement run management endpoints

### Phase 2: Pipeline Integration
1. Modify `ProcessingPipeline` to accept config parameter
2. Store results in `run_results` instead of `dataset_samples`
3. Update comparison logic to work per-run

### Phase 3: Dashboard UI
1. Add Playground page with config editor
2. Add Runs list and comparison view
3. Add sample history in detail view
4. Add "Set as Default" functionality

### Phase 4: Advanced Features
1. Auto-suggestions for prompt improvements based on errors
2. Field-level accuracy tracking
3. Export comparison reports
4. Scheduled test runs

---

## Default Configuration

Initial config to be seeded:

```python
DEFAULT_GEMINI_PROMPT = """Sei un assistente specializzato nell'estrazione dati da Documenti di Trasporto (DDT) italiani.

REGOLE:
1. Estrai SOLO i dati richiesti, non inventare informazioni mancanti
2. Se un campo non è presente nel documento, restituisci null
3. Per le date, converti sempre in formato YYYY-MM-DD
4. Per mittente e destinatario, estrai SOLO la ragione sociale (nome azienda), MAI l'indirizzo
5. Non confondere il Vettore/Trasportatore con il Mittente
6. Se ci sono più indirizzi, dai priorità a "Destinazione Merce" rispetto a "Sede Legale"
7. IMPORTANTE: Se il documento ha più pagine (es. "DDT ASSOCIATA A DDT", "Pag 1/2"), considera TUTTE le pagine come UN UNICO DDT e restituisci UN SOLO oggetto JSON con i dati consolidati
8. Restituisci SEMPRE un singolo oggetto JSON, MAI un array

Rispondi ESCLUSIVAMENTE con JSON valido (un oggetto, non un array), senza markdown, senza spiegazioni."""

DEFAULT_DATALAB_SCHEMA = {
    "type": "object",
    "properties": {
        "mittente": {
            "type": "string",
            "description": "Estrai SOLO la Ragione Sociale (Nome Azienda) che emette il documento..."
        },
        # ... (current schema)
    }
}
```

---

## Migration Strategy

1. **Create tables** with migration script
2. **Seed default config** from current hardcoded values
3. **Create "Legacy" run** with existing `dataset_samples` results
4. **Keep `dataset_samples`** for file metadata, use `run_results` for extractions
5. **Backward compatible** - existing API continues to work, new endpoints are additive

---

## Success Metrics

- **Primary**: Average match score improvement per iteration
- **Secondary**: Reduction in "needs_review" samples
- **Tertiary**: Time to find optimal configuration
