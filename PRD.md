# PRD - DDT Dataset Generation Tool

## EXECUTIVE SUMMARY

**Prodotto:** Tool per generare dataset di training high-quality per fine-tuning small LLM su extraction DDT.

**Problema:** Fine-tuning richiede 300+ esempi validati (PDF → raw OCR → JSON pulito). Validazione manuale di 300 DDT richiederebbe ~25 ore di lavoro.

**Soluzione:** Tool che processa batch PDF attraverso 2 pipeline AI (Datalab vs Azure+Gemini), cross-valida automaticamente gli output concordanti (≥95%), e fornisce dashboard per validazione manuale rapida delle bolle discordanti.

**Output Finale:**
- `training_dataset.jsonl` (formato Alpaca)
- `validation_dataset.jsonl`
- `quality_report.json` (metriche dataset)

**Scope:** One-time use tool per generare dataset, NON sistema di produzione.

---

## DATA CONTRACTS

### DDT Output Schema (Unified)

Questo schema è usato sia da Datalab che da Gemini per garantire output comparabili.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "DDTExtractionSchema",
  "required": [
    "mittente",
    "destinatario",
    "indirizzo_destinazione_completo",
    "data_documento",
    "numero_documento"
  ],
  "properties": {
    "mittente": {
      "type": "string",
      "description": "Solo Ragione Sociale, no indirizzo"
    },
    "destinatario": {
      "type": "string",
      "description": "Solo Ragione Sociale destinazione merce"
    },
    "indirizzo_destinazione_completo": {
      "type": "string",
      "description": "Indirizzo fisico consegna (Via, CAP, Città, Provincia)"
    },
    "data_documento": {
      "type": "string",
      "format": "date",
      "description": "Formato YYYY-MM-DD"
    },
    "data_trasporto": {
      "type": ["string", "null"],
      "format": "date",
      "description": "Formato YYYY-MM-DD o null se assente"
    },
    "numero_documento": {
      "type": "string",
      "description": "Numero Bolla/DDT"
    },
    "numero_ordine": {
      "type": ["string", "null"],
      "description": "Rif. Ordine/Commessa o null"
    },
    "codice_cliente": {
      "type": ["string", "null"],
      "description": "Codice cliente o null"
    }
  }
}
```

---

### Datalab Extraction Schema

Schema da inviare a Datalab API (allineato con Gemini):

```json
{
  "type": "object",
  "title": "DDTExtractionSchema",
  "description": "Schema for DDT structured data extraction",
  "properties": {
    "mittente": {
      "type": "string",
      "description": "Estrai SOLO la Ragione Sociale (Nome Azienda) che emette il documento. Solitamente è il logo principale in alto. Regola: Non includere l'indirizzo, solo il nome (es. 'Barilla S.p.A.'). Ignora il Vettore."
    },
    "destinatario": {
      "type": "string",
      "description": "Estrai SOLO la Ragione Sociale (Nome Azienda) del cliente finale che riceve la merce. Regola: Non includere l'indirizzo, solo il nome (es. 'Mario Rossi SRL'). Se ci sono più nomi, dai priorità a quello nell'area 'Destinazione Merce'."
    },
    "indirizzo_destinazione_completo": {
      "type": "string",
      "description": "Estrai SOLO l'indirizzo fisico di consegna (Via, Civico, CAP, Città, Provincia). Logica: Se l'indirizzo di 'Destinazione Merce' è diverso dalla Sede Legale/Fatturazione, estrai tassativamente quello di Destinazione/Consegna. Non includere il nome dell'azienda qui."
    },
    "data_documento": {
      "type": "string",
      "description": "La data di emissione scritta sul documento (Data bolla/DDT). Cerca 'Data Documento', 'Data DDT'. Formato: Restituisci sempre in formato standard YYYY-MM-DD."
    },
    "data_trasporto": {
      "type": "string",
      "description": "La data specifica di inizio trasporto o data ritiro merce. Cerca 'Data inizio trasporto', 'Data consegna', 'Data partenza'. Logica: Questa data è spesso diversa dalla data del documento. Se non è presente esplicitamente, restituisci null."
    },
    "numero_documento": {
      "type": "string",
      "description": "Il numero identificativo univoco della Bolla o DDT (es. 'N. 1234/A'). Cerca 'Numero Bolla', 'Nr. DDT', 'Doc n.'."
    },
    "numero_ordine": {
      "type": "string",
      "description": "Estrai il codice indicato come 'Rif. Ordine', 'Vs. Ordine', 'Ordine Cliente'. Se non presente, restituisci null."
    },
    "codice_cliente": {
      "type": "string",
      "description": "Estrai il codice indicato come 'Codice Cliente', 'Cod. Cli.' o simili. Se non presente, restituisci null."
    }
  },
  "required": [
    "mittente",
    "destinatario",
    "indirizzo_destinazione_completo",
    "data_documento",
    "numero_documento"
  ]
}
```

---

### Gemini Extraction Schema

Schema identico per Gemini (stesse descrizioni):

```json
{
  "type": "object",
  "title": "DDTExtractionSchema",
  "description": "Schema for DDT structured data extraction",
  "properties": {
    "mittente": {
      "type": "string",
      "description": "Estrai SOLO la Ragione Sociale (Nome Azienda) che emette il documento. Solitamente è il logo principale in alto. Regola: Non includere l'indirizzo, solo il nome (es. 'Barilla S.p.A.'). Ignora il Vettore."
    },
    "destinatario": {
      "type": "string",
      "description": "Estrai SOLO la Ragione Sociale (Nome Azienda) del cliente finale che riceve la merce. Regola: Non includere l'indirizzo, solo il nome (es. 'Mario Rossi SRL'). Se ci sono più nomi, dai priorità a quello nell'area 'Destinazione Merce'."
    },
    "indirizzo_destinazione_completo": {
      "type": "string",
      "description": "Estrai SOLO l'indirizzo fisico di consegna (Via, Civico, CAP, Città, Provincia). Logica: Se l'indirizzo di 'Destinazione Merce' è diverso dalla Sede Legale/Fatturazione, estrai tassativamente quello di Destinazione/Consegna. Non includere il nome dell'azienda qui."
    },
    "data_documento": {
      "type": "string",
      "description": "La data di emissione scritta sul documento (Data bolla/DDT). Cerca 'Data Documento', 'Data DDT'. Formato: Restituisci sempre in formato standard YYYY-MM-DD."
    },
    "data_trasporto": {
      "type": "string",
      "description": "La data specifica di inizio trasporto o data ritiro merce. Cerca 'Data inizio trasporto', 'Data consegna', 'Data partenza'. Logica: Questa data è spesso diversa dalla data del documento. Se non è presente esplicitamente, restituisci null."
    },
    "numero_documento": {
      "type": "string",
      "description": "Il numero identificativo univoco della Bolla o DDT (es. 'N. 1234/A'). Cerca 'Numero Bolla', 'Nr. DDT', 'Doc n.'."
    },
    "numero_ordine": {
      "type": "string",
      "description": "Estrai il codice indicato come 'Rif. Ordine', 'Vs. Ordine', 'Ordine Cliente'. Se non presente, restituisci null."
    },
    "codice_cliente": {
      "type": "string",
      "description": "Estrai il codice indicato come 'Codice Cliente', 'Cod. Cli.' o simili. Se non presente, restituisci null."
    }
  },
  "required": [
    "mittente",
    "destinatario",
    "indirizzo_destinazione_completo",
    "data_documento",
    "numero_documento"
  ]
}
```

---

### Gemini System Prompt

```
Sei un assistente specializzato nell'estrazione dati da Documenti di Trasporto (DDT) italiani.

REGOLE:
1. Estrai SOLO i dati richiesti, non inventare informazioni mancanti
2. Se un campo non è presente nel documento, restituisci null
3. Per le date, converti sempre in formato YYYY-MM-DD
4. Per mittente e destinatario, estrai SOLO la ragione sociale (nome azienda), MAI l'indirizzo
5. Non confondere il Vettore/Trasportatore con il Mittente
6. Se ci sono più indirizzi, dai priorità a "Destinazione Merce" rispetto a "Sede Legale"

Rispondi ESCLUSIVAMENTE con JSON valido, senza markdown, senza spiegazioni.
```

---

## MATCH SCORE ALGORITHM

### Logica di Comparazione

```python
def calculate_match_score(datalab_output: dict, gemini_output: dict) -> tuple[float, list[str]]:
    """
    Calcola match score tra output Datalab e Gemini.

    Returns:
        tuple: (match_score 0.0-1.0, lista campi discordanti)
    """
    fields = [
        "mittente",
        "destinatario",
        "indirizzo_destinazione_completo",
        "data_documento",
        "data_trasporto",
        "numero_documento",
        "numero_ordine",
        "codice_cliente"
    ]

    matches = 0
    discrepancies = []

    for field in fields:
        val_datalab = normalize(datalab_output.get(field))
        val_gemini = normalize(gemini_output.get(field))

        if values_match(val_datalab, val_gemini):
            matches += 1
        else:
            discrepancies.append(field)

    score = matches / len(fields)
    return score, discrepancies


def normalize(value: str | None) -> str | None:
    """Normalizza valore per confronto."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    # Lowercase, strip whitespace, rimuovi punteggiatura extra
    value = value.lower().strip()
    value = re.sub(r'\s+', ' ', value)  # Multiple spaces → single
    value = re.sub(r'[.,;:]+$', '', value)  # Trailing punctuation
    return value if value else None


def values_match(val1: str | None, val2: str | None) -> bool:
    """Confronta due valori con tolleranza."""
    # Entrambi null = match
    if val1 is None and val2 is None:
        return True
    # Uno null, altro no = no match
    if val1 is None or val2 is None:
        return False
    # Exact match dopo normalizzazione
    if val1 == val2:
        return True
    # Fuzzy match per stringhe lunghe (indirizzi)
    if len(val1) > 20 or len(val2) > 20:
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, val1, val2).ratio()
        return ratio >= 0.85
    return False
```

### Soglie Validation

```yaml
validation_thresholds:
  auto_validated: match_score >= 0.95    # 95% campi concordano
  needs_review: match_score < 0.95       # Almeno 1 campo discorda
```

### Logica Decisionale

```
SE match_score >= 0.95:
    status = "auto_validated"
    validated_output = datalab_output  # Default a Datalab
ALTRIMENTI:
    status = "needs_review"
    validated_output = null  # Richiede review manuale
```

---

## RATE LIMITS & CONCURRENCY

### Limiti API (da documentazione)

| API | Limite Reale | Limite Test (conservativo) |
|-----|--------------|---------------------------|
| Datalab | 200 req/60s | 10 req/60s |
| Azure Document Intelligence | ~15 TPS | 1 req/sec |
| Gemini Free Tier | 15 RPM | 10 RPM |

### Configurazione Test Environment

```yaml
rate_limits:
  datalab:
    requests_per_minute: 10
    concurrent_requests: 2
    poll_interval_seconds: 3
    max_polls: 100

  azure_document_intelligence:
    requests_per_second: 1
    concurrent_requests: 2
    retry_on_429: true
    retry_delay_seconds: 5
    max_retries: 3

  gemini:
    requests_per_minute: 10
    concurrent_requests: 2
    retry_on_429: true
    retry_delay_seconds: 10

batch_processing:
  max_parallel_pdfs: 2           # Processa 2 PDF alla volta
  delay_between_pdfs_seconds: 3  # Pausa tra PDF
  delay_between_batches_seconds: 5
```

---

## ERROR HANDLING

### Error Matrix

| Scenario | Azione | Retry | Note |
|----------|--------|-------|------|
| Datalab timeout (>5min) | Log + mark failed | No | Polling max 100 × 3s = 5min |
| Datalab 429 rate limit | Backoff exponential | 3x | Wait 30s, 60s, 120s |
| Datalab extraction failed | Log error + skip | No | Mark sample as "error" |
| Azure 429 rate limit | Backoff exponential | 3x | Wait 5s, 10s, 20s |
| Azure timeout | Log + retry | 2x | Timeout 60s |
| Gemini 429 rate limit | Backoff exponential | 3x | Wait 10s, 30s, 60s |
| Gemini invalid JSON | Re-prompt con hint | 2x | Aggiungi "Rispondi SOLO JSON" |
| Gemini refused | Log + skip | No | Content policy |
| PDF corrotto | Mark rejected | No | validation_status = "error" |
| PDF troppo grande (>200MB) | Mark rejected | No | Split non supportato |
| Network error | Retry | 3x | Qualsiasi API |

### Sample Status Flow

```
pending → processing → auto_validated
                    → needs_review → manually_validated
                                   → rejected
                    → error
```

---

## ENVIRONMENT VARIABLES

```env
# ===================
# SUPABASE
# ===================
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...  # Per backend
SUPABASE_BUCKET=dataset-pdfs

# ===================
# DATALAB
# ===================
DATALAB_API_KEY=your_api_key
DATALAB_API_URL=https://www.datalab.to/api/v1/marker

# ===================
# AZURE DOCUMENT INTELLIGENCE
# ===================
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://xxx.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your_key

# ===================
# GOOGLE GEMINI
# ===================
GOOGLE_API_KEY=your_api_key
GEMINI_MODEL=gemini-1.5-flash  # o gemini-1.5-pro

# ===================
# APP CONFIG
# ===================
ENVIRONMENT=development
LOG_LEVEL=INFO
MAX_PARALLEL_PDFS=2
```

---

## ALPACA TRAINING FORMAT

### Output Format

```jsonl
{"instruction": "Estrai i dati strutturati dal seguente DDT italiano. Campi richiesti: mittente, destinatario, indirizzo_destinazione_completo, data_documento, data_trasporto, numero_documento, numero_ordine, codice_cliente. Rispondi con JSON valido.", "input": "<RAW_OCR_TEXT>", "output": "{\"mittente\": \"LAVAZZA S.p.A.\", \"destinatario\": \"CONAD SOC. COOP.\", ...}"}
{"instruction": "Estrai i dati strutturati dal seguente DDT italiano. Campi richiesti: mittente, destinatario, indirizzo_destinazione_completo, data_documento, data_trasporto, numero_documento, numero_ordine, codice_cliente. Rispondi con JSON valido.", "input": "<RAW_OCR_TEXT>", "output": "{...}"}
```

### Formatter Logic

```python
def format_to_alpaca(sample: DatasetSample, ocr_source: str = "azure") -> dict:
    """
    Converte sample in formato Alpaca per LLaMA Factory.

    Args:
        sample: Sample dal database
        ocr_source: "azure" o "datalab" - quale OCR usare come input

    Returns:
        dict con instruction, input, output
    """
    instruction = (
        "Estrai i dati strutturati dal seguente DDT italiano. "
        "Campi richiesti: mittente, destinatario, indirizzo_destinazione_completo, "
        "data_documento, data_trasporto, numero_documento, numero_ordine, codice_cliente. "
        "Rispondi con JSON valido."
    )

    # Scegli OCR source
    if ocr_source == "azure":
        input_text = sample.azure_raw_ocr
    else:
        input_text = sample.datalab_raw_ocr

    # Output è sempre il validated_output (JSON stringificato)
    output_text = json.dumps(sample.validated_output, ensure_ascii=False)

    return {
        "instruction": instruction,
        "input": input_text,
        "output": output_text
    }
```

### Split Train/Validation

```python
def split_dataset(samples: list, validation_ratio: float = 0.07) -> tuple[list, list]:
    """
    Split random 93% train, 7% validation.
    """
    import random
    random.shuffle(samples)

    val_size = max(1, int(len(samples) * validation_ratio))

    validation = samples[:val_size]
    training = samples[val_size:]

    return training, validation
```

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────┐
│           DASHBOARD (Next.js + shadcn/ui)           │
│                                                     │
│  📤 Upload PDF (drag & drop)                       │
│  📊 Processing Status (progress + stats)           │
│  ✅ Auto-Validated → Export Ready                  │
│  ⚠️  Needs Review → Validation UI                  │
│  📥 Export Dataset (JSONL download)                │
└─────────────────────────────────────────────────────┘
                         ↕ REST API
┌─────────────────────────────────────────────────────┐
│            BACKEND (FastAPI)                        │
│                                                     │
│  POST /api/upload          → Upload PDF            │
│  POST /api/process         → Start processing      │
│  GET  /api/status          → Progress updates      │
│  GET  /api/samples         → List samples          │
│  GET  /api/samples/:id     → Sample detail         │
│  PATCH /api/samples/:id    → Manual validation     │
│  POST /api/export          → Generate JSONL        │
└─────────────────────────────────────────────────────┘
                         ↕
┌─────────────────────────────────────────────────────┐
│        PROCESSING PIPELINE (async)                  │
│                                                     │
│  Per ogni PDF (max 2 paralleli):                   │
│    1. Datalab: OCR + Extraction (async polling)    │
│    2. Azure OCR → Gemini Extraction                │
│    3. Compare outputs → match_score                │
│    4. Auto-validate se score >= 95%                │
│    5. Save to DB                                   │
└─────────────────────────────────────────────────────┘
                         ↕
┌─────────────────────────────────────────────────────┐
│              DATABASE (Supabase)                    │
│                                                     │
│  Table: dataset_samples                            │
│  Table: processing_batches                         │
│  Storage: dataset-pdfs bucket                      │
└─────────────────────────────────────────────────────┘
```

---

## REPOSITORY STRUCTURE

```
ddt-dataset-generator/
├── README.md
├── PRD.md                           # Questo file
├── docker-compose.yml
├── .env.example
│
├── samples/                         # PDF di test (git-ignored)
│   └── .gitkeep
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   │
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app
│   │   ├── config.py                # Settings & env vars
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py            # All endpoints
│   │   │   └── schemas.py           # Pydantic models
│   │   │
│   │   ├── extractors/
│   │   │   ├── __init__.py
│   │   │   ├── datalab.py           # Datalab API client
│   │   │   ├── azure_ocr.py         # Azure Document Intelligence
│   │   │   └── gemini.py            # Gemini extraction
│   │   │
│   │   ├── processing/
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py          # Main processing logic
│   │   │   ├── comparison.py        # Match score calculation
│   │   │   └── alpaca_formatter.py  # JSONL export
│   │   │
│   │   └── database/
│   │       ├── __init__.py
│   │       ├── client.py            # Supabase client
│   │       └── models.py            # DB models
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_extractors.py
│       ├── test_comparison.py
│       └── test_api.py
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   │
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx             # Home: Upload + Status
│   │   │   ├── review/
│   │   │   │   └── page.tsx         # Manual validation UI
│   │   │   └── export/
│   │   │       └── page.tsx         # Export page
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn components
│   │   │   ├── upload-zone.tsx
│   │   │   ├── processing-status.tsx
│   │   │   ├── samples-table.tsx
│   │   │   ├── validation-panel.tsx
│   │   │   └── export-dialog.tsx
│   │   │
│   │   └── lib/
│   │       ├── api.ts               # API client
│   │       └── utils.ts
│   │
│   └── public/
│
└── output/                          # Generated datasets (git-ignored)
    └── .gitkeep
```

---

## DATABASE SCHEMA

### Table: dataset_samples

```sql
CREATE TABLE dataset_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

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
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'auto_validated', 'needs_review', 'manually_validated', 'rejected', 'error')),
    validated_output JSONB,
    validation_source VARCHAR(20) CHECK (validation_source IN ('datalab', 'gemini', 'manual')),
    validator_notes TEXT,

    -- Dataset assignment
    dataset_split VARCHAR(10) CHECK (dataset_split IN ('train', 'validation'))
);

-- Indexes
CREATE INDEX idx_samples_status ON dataset_samples(status);
CREATE INDEX idx_samples_match_score ON dataset_samples(match_score);
CREATE INDEX idx_samples_created_at ON dataset_samples(created_at);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_updated_at
    BEFORE UPDATE ON dataset_samples
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
```

### Table: processing_stats

```sql
CREATE TABLE processing_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

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

-- Single row table
INSERT INTO processing_stats (id) VALUES (gen_random_uuid());
```

### Supabase Storage

```
Bucket: dataset-pdfs
├── uploads/
│   ├── {uuid}.pdf
│   └── ...
```

---

## API ENDPOINTS

### POST /api/upload

Upload singolo PDF.

**Request:**
```
Content-Type: multipart/form-data
file: <PDF binary>
```

**Response:**
```json
{
  "id": "uuid",
  "filename": "ddt_001.pdf",
  "status": "pending"
}
```

---

### POST /api/process

Avvia processing di tutti i PDF pending.

**Request:**
```json
{}
```

**Response:**
```json
{
  "message": "Processing started",
  "pending_count": 5
}
```

---

### GET /api/status

Stato processing corrente.

**Response:**
```json
{
  "is_processing": true,
  "total": 5,
  "processed": 2,
  "auto_validated": 1,
  "needs_review": 1,
  "errors": 0,
  "progress_percent": 40
}
```

---

### GET /api/samples

Lista samples con filtri.

**Query params:**
- `status`: filter by status
- `limit`: max results (default 50)
- `offset`: pagination offset

**Response:**
```json
{
  "samples": [
    {
      "id": "uuid",
      "filename": "ddt_001.pdf",
      "status": "needs_review",
      "match_score": 0.875,
      "discrepancies": ["numero_documento", "data_trasporto"],
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 30,
  "limit": 50,
  "offset": 0
}
```

---

### GET /api/samples/:id

Dettaglio singolo sample per review.

**Response:**
```json
{
  "id": "uuid",
  "filename": "ddt_001.pdf",
  "pdf_url": "https://...",
  "status": "needs_review",
  "match_score": 0.875,
  "discrepancies": ["numero_documento"],
  "datalab_json": {...},
  "gemini_json": {...},
  "datalab_raw_ocr": "...",
  "azure_raw_ocr": "...",
  "validated_output": null
}
```

---

### PATCH /api/samples/:id

Validazione manuale.

**Request:**
```json
{
  "status": "manually_validated",
  "validated_output": {
    "mittente": "...",
    "destinatario": "...",
    ...
  },
  "validation_source": "gemini",
  "validator_notes": "Corretto numero documento"
}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "manually_validated",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

### POST /api/export

Genera e scarica dataset.

**Request:**
```json
{
  "ocr_source": "azure",
  "validation_split": 0.07
}
```

**Response:**
```json
{
  "training_samples": 280,
  "validation_samples": 20,
  "download_urls": {
    "training": "https://...",
    "validation": "https://...",
    "report": "https://..."
  }
}
```

---

## USER INTERFACE

### Home Page (Upload + Status)

```
┌─────────────────────────────────────────────────────┐
│  DDT Dataset Generator                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │                                               │ │
│  │   📄 Drop PDF files here                     │ │
│  │      or click to browse                       │ │
│  │                                               │ │
│  │   [Browse Files]                              │ │
│  │                                               │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  ────────────────────────────────────────────────  │
│                                                     │
│  📊 Processing Status                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/5 (60%)           │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ ✅ 2     │ │ ⚠️ 1     │ │ ❌ 0     │           │
│  │ Auto     │ │ Review   │ │ Errors   │           │
│  └──────────┘ └──────────┘ └──────────┘           │
│                                                     │
│  [Start Processing]  [View Review Queue →]         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

### Review Page

```
┌─────────────────────────────────────────────────────────────────┐
│  Review Samples (3 pending)                          [← Back]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┬────────────────────────────────────────────┐  │
│  │             │  Comparison                                │  │
│  │   PDF       │                                            │  │
│  │   Preview   │  Campo         │ Datalab    │ Gemini  │ Δ │  │
│  │             │  ─────────────────────────────────────────│  │
│  │   [Zoom]    │  mittente      │ LAVAZZA    │ LAVAZZA │ ✅│  │
│  │             │  destinatario  │ CONAD      │ CONAD   │ ✅│  │
│  │             │  numero_doc    │ DDT-1234   │ DDT1234 │ 🚨│  │
│  │             │  data_doc      │ 2025-01-15 │ 2025-01-15│✅│  │
│  │             │  ...           │            │         │   │  │
│  │             │                                            │  │
│  │             ├────────────────────────────────────────────┤  │
│  │             │  Actions:                                  │  │
│  │             │                                            │  │
│  │             │  [✅ Accept Datalab]  [✅ Accept Gemini]  │  │
│  │             │  [✏️ Edit Manually]   [❌ Reject]         │  │
│  │             │                                            │  │
│  │             │  Notes: ________________________________   │  │
│  │             │                                            │  │
│  │             │  [← Previous]  [Next →]                    │  │
│  └─────────────┴────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Export Page

```
┌─────────────────────────────────────────────────────┐
│  Export Dataset                          [← Back]   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📊 Dataset Summary                                 │
│  ┌───────────────────────────────────────────────┐ │
│  │ Total Samples:        300                     │ │
│  │ Auto-validated:       270 (90%)               │ │
│  │ Manually validated:   28                      │ │
│  │ Rejected:             2                       │ │
│  │ Average Match Score:  0.94                    │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  ⚙️ Export Settings                                │
│                                                     │
│  OCR Source for training input:                    │
│  ○ Azure OCR (recommended)                         │
│  ○ Datalab OCR                                     │
│                                                     │
│  Validation split: [7%____▼]                       │
│                                                     │
│  ────────────────────────────────────────────────  │
│                                                     │
│  [📥 Download training_dataset.jsonl]              │
│  [📥 Download validation_dataset.jsonl]            │
│  [📊 Download quality_report.json]                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## QUALITY REPORT FORMAT

```json
{
  "generated_at": "2025-01-15T12:00:00Z",
  "dataset_summary": {
    "total_samples": 300,
    "training_samples": 279,
    "validation_samples": 21,
    "rejected_samples": 0
  },
  "validation_breakdown": {
    "auto_validated": 270,
    "manually_validated": 30,
    "validation_sources": {
      "datalab": 145,
      "gemini": 125,
      "manual": 30
    }
  },
  "quality_metrics": {
    "avg_match_score": 0.943,
    "min_match_score": 0.625,
    "max_match_score": 1.0,
    "score_distribution": {
      "1.0": 180,
      "0.95-0.99": 90,
      "0.90-0.94": 20,
      "below_0.90": 10
    }
  },
  "field_coverage": {
    "mittente": 1.0,
    "destinatario": 1.0,
    "indirizzo_destinazione_completo": 1.0,
    "data_documento": 1.0,
    "numero_documento": 1.0,
    "data_trasporto": 0.72,
    "numero_ordine": 0.85,
    "codice_cliente": 0.68
  },
  "processing_stats": {
    "avg_processing_time_seconds": 14.2,
    "total_processing_time_minutes": 71,
    "datalab_avg_time_ms": 8500,
    "azure_avg_time_ms": 3200,
    "gemini_avg_time_ms": 2100
  },
  "estimated_cost": {
    "datalab_usd": 1.35,
    "azure_usd": 0.45,
    "gemini_usd": 0.0,
    "total_usd": 1.80
  }
}
```

---

## DEVELOPMENT MILESTONES

### Milestone 1: Foundation (Day 1-2)

- [ ] Repository setup con struttura cartelle
- [ ] Supabase: create tables + storage bucket
- [ ] Backend: FastAPI skeleton + config
- [ ] Backend: Supabase client
- [ ] Test: connessione DB funzionante

### Milestone 2: Extractors (Day 3-4)

- [ ] `datalab.py`: client con polling asincrono
- [ ] `azure_ocr.py`: Document Intelligence client
- [ ] `gemini.py`: extraction con schema
- [ ] `comparison.py`: match score algorithm
- [ ] Test: process 1 PDF attraverso entrambe pipeline

### Milestone 3: Processing Pipeline (Day 5)

- [ ] `pipeline.py`: orchestrazione completa
- [ ] Rate limiting implementation
- [ ] Error handling robusto
- [ ] `alpaca_formatter.py`: export JSONL
- [ ] Test: process 5 PDF con export

### Milestone 4: API (Day 6)

- [ ] Tutti gli endpoint implementati
- [ ] Upload file to Supabase Storage
- [ ] Background processing task
- [ ] Test: full API flow con curl/Postman

### Milestone 5: Frontend (Day 7-9)

- [ ] Next.js + shadcn/ui setup
- [ ] Home page: upload + status
- [ ] Review page: validation UI
- [ ] Export page: download datasets
- [ ] Test: full E2E flow

### Milestone 6: Polish (Day 10)

- [ ] Docker compose setup
- [ ] Documentation
- [ ] Bug fixes
- [ ] Test con 20+ PDF reali

---

## DEFINITION OF DONE

Il progetto è completo quando:

- [ ] Upload PDF funziona (singolo + batch)
- [ ] Processing automatico con entrambe pipeline
- [ ] Match score >= 95% → auto-validated
- [ ] Match score < 95% → needs_review con UI comparison
- [ ] Validation UI permette: accept Datalab, accept Gemini, edit manual, reject
- [ ] Export genera JSONL formato Alpaca valido
- [ ] Quality report con metriche complete
- [ ] Rate limiting previene errori 429
- [ ] Error handling non blocca il batch
- [ ] Testato con almeno 20 PDF reali

---

## ESTIMATED COSTS

Per 300 DDT:

| Service | Cost |
|---------|------|
| Datalab | 300 × $0.006 = $1.80 |
| Azure Document Intelligence | 300 × $0.001 = $0.30 |
| Gemini | $0 (free tier) |
| Supabase | $0 (free tier) |
| **TOTAL** | **~$2.10** |

---

## NOTES

- Questo è un tool one-time per generazione dataset, non un sistema di produzione
- I rate limits sono conservativi per ambiente di test
- La cartella `samples/` è per i PDF di test (iniziare con 5)
- Output in `output/` è git-ignored
