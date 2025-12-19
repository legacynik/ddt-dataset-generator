# CLAUDE.md - DDT Dataset Generator

## Project Overview

Tool per generare dataset di training (formato Alpaca JSONL) per fine-tuning LLM su estrazione dati da DDT italiani.

**Stack:**
- Backend: FastAPI + Python 3.11
- Frontend: Next.js 14 + shadcn/ui + TailwindCSS
- Database: Supabase (Postgres + Storage)
- AI: Datalab API, Azure Document Intelligence, Google Gemini

## Quick Commands

```bash
# Backend
cd backend
source venv/bin/activate  # o: uv venv && source .venv/bin/activate
uvicorn src.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev

# Tests
cd backend && pytest tests/ -v

# Docker
docker-compose up
```

## Project Structure

```
ddt-dataset-generator/
├── PRD.md              # Product Requirements (fonte verità per specs)
├── SPEC.md             # Task breakdown dettagliato
├── CLAUDE.md           # Questo file
├── samples/            # PDF di test (6 file)
├── output/             # Dataset generati (git-ignored)
├── backend/            # FastAPI Python
└── frontend/           # Next.js React
```

## Critical Files Reference

| File | Purpose |
|------|---------|
| `PRD.md` | Schema JSON DDT, prompts, algoritmi, API specs |
| `SPEC.md` | Checklist task per milestone |
| `backend/src/config.py` | Environment variables |
| `backend/src/extractors/schemas.py` | DDT extraction schema |
| `backend/src/processing/comparison.py` | Match score algorithm |
| `backend/src/api/routes.py` | All API endpoints |

## Development Rules

### General
- Leggi SEMPRE `PRD.md` prima di implementare una feature
- Segui le task in `SPEC.md` in ordine
- Usa typing hints ovunque in Python
- Preferisci async/await per I/O operations
- Max 2 richieste parallele alle API esterne (rate limiting)

### Backend (Python/FastAPI)
- Usa `httpx` per HTTP calls (async)
- Usa `pydantic` per validazione
- Gestisci SEMPRE errori API con try/except
- Log con `logging` module, level INFO
- Nomi file: snake_case
- Nomi classi: PascalCase

### Frontend (Next.js/React)
- Usa App Router (not pages)
- Usa shadcn/ui per componenti
- Usa TanStack Query per data fetching
- Nomi componenti: PascalCase
- Nomi file componenti: kebab-case.tsx

### Database
- UUID per tutti gli ID
- Timestamps: `created_at`, `updated_at` automatici
- Status enum: `pending`, `processing`, `auto_validated`, `needs_review`, `manually_validated`, `rejected`, `error`

## Key Algorithms

### Match Score (da PRD.md)
```python
# Soglia auto-validation: >= 0.95 (95%)
# Fuzzy match threshold: 0.85 per stringhe > 20 chars
# Campi: 8 totali, score = matches / 8
```

### Rate Limits (conservative per test)
```yaml
datalab: 10 req/min, 2 concurrent
azure: 1 req/sec, 2 concurrent
gemini: 10 req/min, 2 concurrent
batch: max 2 PDF paralleli
```

## Environment Variables Required

```
SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY
DATALAB_API_KEY
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT, AZURE_DOCUMENT_INTELLIGENCE_KEY
GOOGLE_API_KEY
```

## Testing Approach

1. **Unit tests**: Ogni modulo in `backend/tests/`
2. **Integration**: Test con PDF reali in `samples/`
3. **E2E**: Full flow upload → process → validate → export

## Common Errors & Solutions

| Error | Solution |
|-------|----------|
| Datalab timeout | Aumenta max_polls o poll_interval |
| Azure 429 | Riduci concurrency, aggiungi delay |
| Gemini invalid JSON | Retry con prompt più esplicito |
| Supabase RLS | Usa service_key per backend |

## API Endpoints Summary

```
POST /api/upload          Upload PDF
POST /api/process         Start batch processing
GET  /api/status          Processing progress
GET  /api/samples         List all samples
GET  /api/samples/{id}    Sample detail
PATCH /api/samples/{id}   Manual validation
POST /api/export          Generate JSONL dataset
GET  /health              Health check
```

## Workflow per Nuove Feature

1. Leggi task in `SPEC.md`
2. Consulta specs in `PRD.md`
3. Implementa con tests
4. Marca task come completata in `SPEC.md`
5. Commit con messaggio: `feat(module): description`

## Git Conventions

```bash
# Branch naming
feature/m1-database-setup
feature/m2-extractors
fix/datalab-timeout

# Commit messages
feat(extractors): add Datalab client with polling
fix(pipeline): handle Azure 429 rate limit
test(comparison): add edge case tests
docs: update README with setup instructions
```

## Agent Assignments

| Agent | Scope |
|-------|-------|
| `backend-developer` | M1.2, M1.3, M2.*, M3.*, M4.* |
| `frontend-developer` | M5.* |
| `db-architect` | M1.1 |
| `test-engineer` | M6.2 |
| `devops` | M6.1 |

## Notes

- Questo è un tool one-time, non production system
- Rate limits conservativi: meglio lento che bloccato
- Iniziare con 6 PDF in `samples/`, poi scalare
- Output JSONL deve essere compatibile con LLaMA Factory
