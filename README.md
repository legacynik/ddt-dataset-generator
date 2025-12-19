# DDT Dataset Generator

Full-stack application for processing Italian transport documents (DDT) and generating Alpaca-format training datasets.

## Stack

- **Backend**: FastAPI, Supabase, Datalab, Azure Document Intelligence, Gemini
- **Frontend**: Next.js 14, TypeScript, TailwindCSS, shadcn/ui

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env  # Configure your API keys
uvicorn src.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
SUPABASE_BUCKET=dataset-pdfs
DATALAB_API_URL=
DATALAB_API_KEY=
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=
AZURE_DOCUMENT_INTELLIGENCE_KEY=
GOOGLE_API_KEY=
```
