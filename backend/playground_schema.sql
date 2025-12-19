-- ===========================================
-- DDT Dataset Generator - Playground Schema
-- ===========================================
-- Run this AFTER supabase_schema.sql
-- Adds support for multi-extractor testing
-- ===========================================

-- ===========================================
-- MODIFY: dataset_samples
-- ===========================================
-- Add ground truth and OCR completion tracking

ALTER TABLE dataset_samples
ADD COLUMN IF NOT EXISTS ground_truth_json JSONB,
ADD COLUMN IF NOT EXISTS ground_truth_validated_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS ground_truth_notes TEXT,
ADD COLUMN IF NOT EXISTS ocr_completed_at TIMESTAMPTZ;

-- Rename datalab_json to datalab_structured for clarity
ALTER TABLE dataset_samples
RENAME COLUMN datalab_json TO datalab_structured;

COMMENT ON COLUMN dataset_samples.ground_truth_json IS 'Manually validated correct extraction (source of truth)';
COMMENT ON COLUMN dataset_samples.ocr_completed_at IS 'When OCR was cached (Azure + Datalab)';

-- ===========================================
-- TABLE: extractors
-- ===========================================
CREATE TABLE IF NOT EXISTS extractors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Identity
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,

    -- Type: gemini, openrouter, ollama, datalab, custom
    type VARCHAR(20) NOT NULL
        CHECK (type IN ('gemini', 'openrouter', 'ollama', 'datalab', 'custom')),

    -- Model identifier
    model_id VARCHAR(100) NOT NULL,

    -- Configuration
    system_prompt TEXT NOT NULL,
    extraction_schema JSONB NOT NULL,
    temperature DECIMAL(3,2) DEFAULT 0.1,
    max_tokens INTEGER DEFAULT 2048,

    -- API settings (for openrouter/ollama/custom)
    api_base_url TEXT,
    api_key_env VARCHAR(50),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_baseline BOOLEAN DEFAULT FALSE,

    -- Calculated accuracy (updated after benchmarks)
    overall_accuracy DECIMAL(5,4),
    last_benchmark_at TIMESTAMPTZ
);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS trigger_update_extractors_updated_at ON extractors;
CREATE TRIGGER trigger_update_extractors_updated_at
    BEFORE UPDATE ON extractors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

COMMENT ON TABLE extractors IS 'Configurable LLM extractors for DDT data extraction';

-- ===========================================
-- TABLE: extraction_runs
-- ===========================================
CREATE TABLE IF NOT EXISTS extraction_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMPTZ,

    -- Identity
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Configuration
    extractor_id UUID NOT NULL REFERENCES extractors(id) ON DELETE RESTRICT,

    -- Scope (NULL = all samples with cached OCR)
    sample_ids UUID[],

    -- Status
    status VARCHAR(20) DEFAULT 'pending' NOT NULL
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

    -- Aggregated results
    total_samples INTEGER DEFAULT 0,
    processed INTEGER DEFAULT 0,
    successful INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,

    -- Accuracy metrics
    accuracy_vs_ground_truth DECIMAL(5,4),
    accuracy_vs_baseline DECIMAL(5,4),
    avg_processing_time_ms INTEGER,

    notes TEXT
);

COMMENT ON TABLE extraction_runs IS 'Test runs for benchmarking different extractors';

-- ===========================================
-- TABLE: extraction_results
-- ===========================================
CREATE TABLE IF NOT EXISTS extraction_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Links
    run_id UUID NOT NULL REFERENCES extraction_runs(id) ON DELETE CASCADE,
    sample_id UUID NOT NULL REFERENCES dataset_samples(id) ON DELETE CASCADE,
    extractor_id UUID NOT NULL REFERENCES extractors(id) ON DELETE RESTRICT,

    -- Results
    extracted_json JSONB,
    processing_time_ms INTEGER,
    error_message TEXT,
    success BOOLEAN DEFAULT TRUE,

    -- Comparison scores
    match_vs_ground_truth DECIMAL(5,4),
    match_vs_baseline DECIMAL(5,4),
    field_matches JSONB,

    UNIQUE(run_id, sample_id)
);

COMMENT ON TABLE extraction_results IS 'Extraction results per sample per run';

-- ===========================================
-- TABLE: field_accuracy
-- ===========================================
CREATE TABLE IF NOT EXISTS field_accuracy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    extractor_id UUID NOT NULL REFERENCES extractors(id) ON DELETE CASCADE,
    field_name VARCHAR(50) NOT NULL,

    correct_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    accuracy DECIMAL(5,4),

    UNIQUE(extractor_id, field_name)
);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS trigger_update_field_accuracy_updated_at ON field_accuracy;
CREATE TRIGGER trigger_update_field_accuracy_updated_at
    BEFORE UPDATE ON field_accuracy
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

COMMENT ON TABLE field_accuracy IS 'Per-field accuracy tracking for each extractor';

-- ===========================================
-- INDEXES
-- ===========================================
CREATE INDEX IF NOT EXISTS idx_extraction_results_run ON extraction_results(run_id);
CREATE INDEX IF NOT EXISTS idx_extraction_results_sample ON extraction_results(sample_id);
CREATE INDEX IF NOT EXISTS idx_extraction_results_extractor ON extraction_results(extractor_id);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_extractor ON extraction_runs(extractor_id);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_status ON extraction_runs(status);
CREATE INDEX IF NOT EXISTS idx_field_accuracy_extractor ON field_accuracy(extractor_id);
CREATE INDEX IF NOT EXISTS idx_extractors_type ON extractors(type);
CREATE INDEX IF NOT EXISTS idx_extractors_active ON extractors(is_active);

-- ===========================================
-- SEED: Default Extractors
-- ===========================================

-- Gemini 2.0 Flash (default)
INSERT INTO extractors (name, description, type, model_id, system_prompt, extraction_schema, temperature, api_key_env, is_active)
VALUES (
    'Gemini 2.0 Flash',
    'Google Gemini 2.0 Flash - veloce e accurato',
    'gemini',
    'gemini-2.0-flash-exp',
    'Sei un assistente specializzato nell''estrazione dati da Documenti di Trasporto (DDT) italiani.

REGOLE:
1. Estrai SOLO i dati richiesti, non inventare informazioni mancanti
2. Se un campo non è presente nel documento, restituisci null
3. Per le date, converti sempre in formato YYYY-MM-DD
4. Per mittente e destinatario, estrai SOLO la ragione sociale (nome azienda), MAI l''indirizzo
5. Non confondere il Vettore/Trasportatore con il Mittente
6. Se ci sono più indirizzi, dai priorità a "Destinazione Merce" rispetto a "Sede Legale"
7. IMPORTANTE: Se il documento ha più pagine (es. "DDT ASSOCIATA A DDT", "Pag 1/2"), considera TUTTE le pagine come UN UNICO DDT e restituisci UN SOLO oggetto JSON con i dati consolidati
8. Restituisci SEMPRE un singolo oggetto JSON, MAI un array

Rispondi ESCLUSIVAMENTE con JSON valido (un oggetto, non un array), senza markdown, senza spiegazioni.',
    '{
        "type": "object",
        "properties": {
            "mittente": {"type": "string", "description": "Ragione sociale del mittente (chi emette il DDT)"},
            "destinatario": {"type": "string", "description": "Ragione sociale del destinatario"},
            "indirizzo_destinazione_completo": {"type": "string", "description": "Indirizzo completo di consegna"},
            "data_documento": {"type": "string", "description": "Data del documento (YYYY-MM-DD)"},
            "data_trasporto": {"type": "string", "description": "Data inizio trasporto (YYYY-MM-DD)"},
            "numero_documento": {"type": "string", "description": "Numero del DDT"},
            "numero_ordine": {"type": "string", "description": "Numero ordine cliente"},
            "codice_cliente": {"type": "string", "description": "Codice cliente"}
        },
        "required": ["mittente", "destinatario", "indirizzo_destinazione_completo", "data_documento", "numero_documento"]
    }'::jsonb,
    0.1,
    'GOOGLE_API_KEY',
    true
) ON CONFLICT (name) DO UPDATE SET
    model_id = EXCLUDED.model_id,
    system_prompt = EXCLUDED.system_prompt,
    updated_at = NOW();

-- Datalab (baseline)
INSERT INTO extractors (name, description, type, model_id, system_prompt, extraction_schema, is_active, is_baseline)
VALUES (
    'Datalab Marker',
    'Datalab Marker API - baseline per confronto',
    'datalab',
    'datalab-marker',
    'N/A - Uses Datalab structured extraction',
    '{
        "type": "object",
        "properties": {
            "mittente": {"type": "string", "description": "Ragione sociale del mittente"},
            "destinatario": {"type": "string", "description": "Ragione sociale del destinatario"},
            "indirizzo_destinazione_completo": {"type": "string", "description": "Indirizzo completo di consegna"},
            "data_documento": {"type": "string", "description": "Data del documento (YYYY-MM-DD)"},
            "data_trasporto": {"type": "string", "description": "Data inizio trasporto (YYYY-MM-DD)"},
            "numero_documento": {"type": "string", "description": "Numero del DDT"},
            "numero_ordine": {"type": "string", "description": "Numero ordine cliente"},
            "codice_cliente": {"type": "string", "description": "Codice cliente"}
        }
    }'::jsonb,
    true,
    true
) ON CONFLICT (name) DO UPDATE SET
    is_baseline = true,
    updated_at = NOW();

-- ===========================================
-- VERIFY INSTALLATION
-- ===========================================
SELECT 'Tables created:' as info;
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('extractors', 'extraction_runs', 'extraction_results', 'field_accuracy');

SELECT 'Extractors seeded:' as info;
SELECT name, type, model_id, is_baseline FROM extractors;
