# Med Insight AI

Privacy-first medical document analysis with **RAG** (LangChain + ChromaDB). Upload lab PDFs, ask questions, and get answers with **cited sources** from a medical dictionary (NIH/Mayo style).

## Features

- **Upload medical lab PDFs** – Native text extraction with **OCR** fallback for scanned pages
- **PII redaction** – Names and phone numbers redacted before processing (upload text and query)
- **RAG over medical dictionary** – Answers grounded in an ingested medical knowledge base
- **Source section** – Every response includes a *Source* section citing the medical database
- **Simplified vs Technical view** – Toggle result display for plain-language or technical context
- **WCAG-friendly, calming UI** – Accessible, clean, privacy-first frontend

## Stack

- **Frontend:** React 18 + Vite + TypeScript
- **Backend:** FastAPI (Python)
- **RAG:** LangChain + ChromaDB; embeddings: sentence-transformers (all-MiniLM-L6-v2)
- **OCR:** pdf2image + Tesseract (optional; install Tesseract on the host)
- **PII:** Presidio (optional) + regex for phones and common lab patterns

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Install **Tesseract** for OCR (scanned PDFs):

- **macOS:** `brew install tesseract`
- **Ubuntu:** `sudo apt install tesseract-ocr`

Ingest the medical dictionary into ChromaDB (run once):

```bash
python -m scripts.ingest_medical_dict
```

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Use the proxy in `vite.config.ts` so `/api` goes to the backend.

### 3. Optional: LLM for answers

By default, the app returns retrieved context and sources without an LLM. To get natural-language answers:

- Install [Ollama](https://ollama.ai) and run e.g. `ollama run llama3.2`, or
- Change `app/services/rag_service.py` to use OpenAI or another LLM.

## Project layout

```
backend/
  app/
    api/          # upload, query, health
    core/         # config
    middleware/   # PII redaction (optional middleware)
    services/    # pii_redaction, pdf_ocr, vector_store, rag_service
  data/           # medical_dictionary_sample.json
  scripts/        # ingest_medical_dict.py
frontend/
  src/
    components/  # UploadSection, QuerySection, ResultSection
```

## Privacy

- Uploaded PDFs are not stored on disk; only **redacted** extracted text is chunked and embedded.
- Query text is redacted for PII before being sent to the RAG pipeline.
- Use Presidio for stronger NER-based redaction; regex handles phones and common “Patient: …” patterns otherwise.

## Medical dictionary

The sample dictionary in `backend/data/medical_dictionary_sample.json` includes common lab terms (e.g. Hemoglobin, Creatinine, TSH). You can extend it or replace it with NIH/UMLS/MeSH data; the ingest script expects JSON with `term`, `definition`, `source`, and optional `category`.

## License

MIT.
