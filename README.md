# DDT Dataset Generator

## Il Problema

Addestrare modelli di AI per estrarre dati da **DDT (Documenti Di Trasporto)** italiani richiede dataset di alta qualità. Tuttavia:

- **Non esistono dataset pubblici** per DDT italiani
- I DDT variano enormemente tra aziende (layout, campi, formati)
- Creare manualmente un dataset è **costoso e lento**
- La validazione richiede confronto tra più fonti OCR

## La Soluzione

Questo tool automatizza la creazione di dataset per DDT utilizzando **multi-OCR cross-validation**:

1. **Carica** i tuoi PDF di DDT
2. **Estrazione parallela** con 3 servizi:
   - Datalab (OCR + estrazione strutturata)
   - Azure Document Intelligence (OCR)
   - Google Gemini (estrazione da testo OCR)
3. **Confronto automatico** tra Datalab e Gemini
4. **Auto-validazione** se match score ≥ 95%
5. **Review manuale** solo per discrepanze
6. **Export** in formato Alpaca (train.jsonl + validation.jsonl)

## Campi Estratti

| Campo | Descrizione |
|-------|-------------|
| `mittente` | Ragione sociale del mittente |
| `destinatario` | Ragione sociale del destinatario |
| `indirizzo_destinazione_completo` | Indirizzo completo di consegna |
| `data_documento` | Data del documento |
| `data_trasporto` | Data di inizio trasporto |
| `numero_documento` | Numero del DDT |
| `numero_ordine` | Riferimento ordine cliente |
| `codice_cliente` | Codice cliente |

## Stack

- **Backend**: FastAPI, Supabase, Datalab API, Azure Document Intelligence, Google Gemini
- **Frontend**: Next.js 14, TypeScript, TailwindCSS, shadcn/ui

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Configura `.env` con le tue API keys (vedi `.env.example`).

## Output

```
output/
├── train.jsonl        # 80% dei sample validati
├── validation.jsonl   # 20% dei sample validati
└── quality_report.json
```

Formato Alpaca:
```json
{
  "instruction": "Estrai i dati strutturati dal seguente DDT...",
  "input": "[testo OCR del documento]",
  "output": "{\"mittente\": \"...\", \"destinatario\": \"...\", ...}"
}
```
