# Supabase Setup Instructions

## Step 1: Execute SQL Schema

1. Vai a [Supabase Dashboard](https://supabase.com/dashboard/project/iexbwkjjtxhragdkoxmi)
2. Nella sidebar, clicca **SQL Editor**
3. Clicca **New query**
4. Copia tutto il contenuto di `backend/supabase_schema.sql`
5. Incolla nell'editor e clicca **Run**

### Verifica

Esegui questa query per verificare:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('dataset_samples', 'processing_stats');
```

Dovresti vedere 2 righe.

---

## Step 2: Create Storage Bucket

1. Nella sidebar, clicca **Storage**
2. Clicca **Create a new bucket**
3. Configura:
   - **Name:** `dataset-pdfs`
   - **Public:** ❌ NO (private)
   - **File size limit:** `200 MB`
   - **Allowed MIME types:** `application/pdf`
4. Clicca **Create bucket**

### Verifica

Dovresti vedere il bucket "dataset-pdfs" nella lista.

---

## Step 3: (Optional) Configure RLS Policies

Per ora usiamo `SUPABASE_SERVICE_KEY` nel backend, che bypassa RLS.
Se in futuro vuoi usare RLS:

```sql
-- Enable RLS
ALTER TABLE dataset_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_stats ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (backend)
CREATE POLICY "Service role full access" ON dataset_samples
FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON processing_stats
FOR ALL USING (auth.role() = 'service_role');
```

---

## Done! ✅

Le tue tabelle Supabase sono pronte. Prossimo step: backend setup.
