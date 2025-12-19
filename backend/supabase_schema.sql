-- ===========================================
-- DDT Dataset Generator - Supabase Schema
-- ===========================================
-- Execute this script in Supabase SQL Editor
-- Project: https://iexbwkjjtxhragdkoxmi.supabase.co
--
-- Order of execution:
-- 1. Tables
-- 2. Triggers
-- 3. Storage bucket (via Dashboard UI)
-- ===========================================

-- Drop existing tables if re-running (use with caution)
-- DROP TABLE IF EXISTS dataset_samples CASCADE;
-- DROP TABLE IF EXISTS processing_stats CASCADE;

-- ===========================================
-- TABLE: dataset_samples
-- ===========================================
CREATE TABLE IF NOT EXISTS dataset_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- File info
    filename VARCHAR(255) NOT NULL,
    pdf_storage_path TEXT NOT NULL,
    file_size_bytes INTEGER,

    -- Pipeline Datalab
    datalab_raw_ocr TEXT,
    datalab_json JSONB,
    datalab_processing_time_ms INTEGER,
    datalab_error TEXT,

    -- Pipeline Azure + Gemini
    azure_raw_ocr TEXT,
    azure_processing_time_ms INTEGER,
    azure_error TEXT,
    gemini_json JSONB,
    gemini_processing_time_ms INTEGER,
    gemini_error TEXT,

    -- Comparison
    match_score DECIMAL(5,4),  -- 0.0000 to 1.0000
    discrepancies TEXT[],      -- Array of field names

    -- Validation
    status VARCHAR(20) DEFAULT 'pending' NOT NULL
        CHECK (status IN ('pending', 'processing', 'auto_validated', 'needs_review', 'manually_validated', 'rejected', 'error')),
    validated_output JSONB,
    validation_source VARCHAR(20) CHECK (validation_source IN ('datalab', 'gemini', 'manual')),
    validator_notes TEXT,

    -- Dataset assignment
    dataset_split VARCHAR(10) CHECK (dataset_split IN ('train', 'validation'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_samples_status ON dataset_samples(status);
CREATE INDEX IF NOT EXISTS idx_samples_match_score ON dataset_samples(match_score);
CREATE INDEX IF NOT EXISTS idx_samples_created_at ON dataset_samples(created_at DESC);

-- Comment
COMMENT ON TABLE dataset_samples IS 'Stores DDT PDF samples with dual extraction outputs and validation status';

-- ===========================================
-- TABLE: processing_stats
-- ===========================================
CREATE TABLE IF NOT EXISTS processing_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    total_samples INTEGER DEFAULT 0,
    processed INTEGER DEFAULT 0,
    auto_validated INTEGER DEFAULT 0,
    needs_review INTEGER DEFAULT 0,
    manually_validated INTEGER DEFAULT 0,
    rejected INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,

    avg_match_score DECIMAL(5,4),
    total_processing_time_ms BIGINT,

    is_processing BOOLEAN DEFAULT FALSE
);

-- Single row table for global stats
INSERT INTO processing_stats (id, total_samples, processed)
VALUES (gen_random_uuid(), 0, 0)
ON CONFLICT DO NOTHING;

COMMENT ON TABLE processing_stats IS 'Global processing statistics (single row table)';

-- ===========================================
-- TRIGGER: Auto-update updated_at timestamp
-- ===========================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to dataset_samples
DROP TRIGGER IF EXISTS trigger_update_samples_updated_at ON dataset_samples;
CREATE TRIGGER trigger_update_samples_updated_at
    BEFORE UPDATE ON dataset_samples
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Apply trigger to processing_stats
DROP TRIGGER IF EXISTS trigger_update_stats_updated_at ON processing_stats;
CREATE TRIGGER trigger_update_stats_updated_at
    BEFORE UPDATE ON processing_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ===========================================
-- VERIFY INSTALLATION
-- ===========================================
-- Run these queries to verify:

-- Check tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('dataset_samples', 'processing_stats');

-- Check indexes
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'dataset_samples';

-- Verify processing_stats has 1 row
SELECT * FROM processing_stats;

-- ===========================================
-- STORAGE BUCKET SETUP (Manual via Dashboard)
-- ===========================================
-- 1. Go to: Storage > Create new bucket
-- 2. Name: dataset-pdfs
-- 3. Public: NO (private)
-- 4. File size limit: 200 MB
-- 5. Allowed MIME types: application/pdf
--
-- RLS Policies (optional for now, use service_key):
-- - Allow authenticated users to upload
-- - Allow authenticated users to read
-- ===========================================
