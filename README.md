# docRAG v1 — Flat RAG

The first version of docRAG: the simplest possible PDF question-answering pipeline. Upload a PDF, it gets chunked and embedded, then you ask questions and get answers pulled from whichever chunks look most similar to the question.

There is no section awareness, no citation structure, and no async processing — every request runs inline, blocking until it's done. This version exists to establish the baseline: the model and infrastructure aren't the hard part of RAG. What you do to the document *before* it hits the vector store is.

## How It Works

```
PDF ─upload─▶ PyMuPDF text extraction ─▶ token-window chunking (with overlap)
                                                    │
                                                    ▼
                                   all-MiniLM-L6-v2 embeddings (384-dim)
                                                    │
                                                    ▼
                                          stored in Qdrant

Question ─▶ same embedding model ─▶ cosine similarity search in Qdrant
                                                    │
                                                    ▼
                                   top-K chunks + question ──▶ Ollama ──▶ Answer
```

Both ingestion and querying happen **synchronously, inline in the request** — there's no task queue. Uploading a large PDF blocks the HTTP call until every chunk is extracted, embedded, and stored.

### The core limitation

Chunking is purely a fixed-size sliding window over whitespace-separated tokens (`CHUNK_TOKENS` wide, `CHUNK_OVERLAP_TOKENS` of overlap) applied to the entire extracted text, with **zero awareness of document structure**. A chunk can — and regularly does — straddle a paper's abstract, its methods section, and its references in the same window. There's no metadata distinguishing a claim from a citation from a section heading; by the time text reaches Qdrant, all of that structure is gone. Retrieval is pure vector similarity over these undifferentiated windows, so a query about "the method" can just as easily surface a chunk that's mostly bibliography.

This is deliberate, not an oversight — see [`docRAG_v2`](https://github.com/AnshulPatil2005/docRAG_v2), which fixes the *engineering* (async ingestion, OCR, a real frontend) while deliberately leaving this flat chunking model in place, and [`docRAG_v3`](https://github.com/AnshulPatil2005/docRAG_v3), which is the version that actually addresses it with a knowledge-graph layer.

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| API | FastAPI | Two endpoints: upload, ask |
| PDF text extraction | PyMuPDF (`fitz`) | Text-layer extraction only — no OCR, so scanned/image-only PDFs yield little or no text |
| Chunking | Custom, in-process | Fixed-size token windows with overlap, no section/heading awareness |
| Embeddings | Sentence-Transformers (`all-MiniLM-L6-v2`, 384-dim) | Local, free, same model used for chunks and queries |
| Vector store | Qdrant | Cosine similarity search |
| LLM | Ollama (local) | Generates the final answer from retrieved chunks |

## Project Structure

```
docRAG_v1_IDP/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, router mount
│   │   ├── config.py             # Settings read from environment variables
│   │   ├── routes.py             # POST /upload, POST /ask, GET /health
│   │   └── services/
│   │       ├── pdf_extract.py    # PyMuPDF text extraction
│   │       ├── chunking.py       # Fixed-size token-window chunking
│   │       ├── embeddings.py     # Sentence-Transformers model loading + encode
│   │       ├── vector_store.py   # Qdrant collection management, upsert, search
│   │       └── llm.py            # Ollama chat client
│   ├── tests/
│   │   └── test_api.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── index.html                # Minimal single-page upload/ask tester (no framework)
├── docker-compose.yml             # qdrant, ollama, api, frontend
├── .env.example
└── Makefile
```

## Requirements

- Docker & Docker Compose
- (Optional) `make` for the `Makefile` shortcuts

## Setup

Copy `.env.example` to `.env` if you want to override any defaults — everything has a working default already baked into `docker-compose.yml`.

```env
# ----- Qdrant -----
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=documents

# ----- LLM (Ollama, local) -----
OLLAMA_BASE_URL=http://ollama:11434
LLM_MODEL=llama3

# ----- Embeddings -----
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ----- RAG tuning -----
CHUNK_TOKENS=500
CHUNK_OVERLAP_TOKENS=50
RAG_TOP_K=5

# ----- Upload -----
UPLOAD_DIR=/app/uploads
```

There's no OpenRouter/cloud option in this version — Ollama is the only LLM provider.

## Running

```bash
docker-compose up -d --build
```

This launches:

| Service | Port | Notes |
|---|---|---|
| Qdrant | 6333 | Vector database |
| Ollama | 11434 | Local LLM inference |
| API | 8000 | FastAPI backend |
| Frontend | 3000 | Static tester page (plain HTML/JS, no build step) |

Pull the LLM model after startup:
```bash
docker-compose exec ollama ollama pull llama3
```

Or with the Makefile: `make up` / `make down` / `make build` / `make logs`.

Open http://localhost:3000 for the upload/ask tester, or http://localhost:8000/docs for the Swagger UI.

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/upload` | POST | Upload a PDF — processed synchronously; the response only returns once extraction, chunking, and embedding are all done |
| `/ask` | POST | Ask a question; optionally scope it to one `doc_id` |

### Example calls

**Upload:**
```bash
curl -X POST "http://localhost:8000/upload" -F "file=@document.pdf"
```
```json
{ "doc_id": "3f9c2a1e8b4d4f0a9c1e2b3a4d5e6f70", "chunks_stored": 14 }
```

**Ask:**
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "doc_id": "optional-doc-id"}'
```
```json
{
  "answer": "...",
  "sources": [
    { "doc_id": "3f9c2a1e...", "chunk_index": 3, "text_snippet": "..." }
  ]
}
```

`doc_id` is optional on `/ask` — omit it to search across every uploaded document at once.

## Testing

```bash
docker-compose run api pytest
```

`backend/tests/test_api.py` covers the request validation (non-PDF rejected, blank question rejected) and the chunker's windowing/overlap behavior directly, without needing a live Qdrant/Ollama connection.

## Troubleshooting

**`model 'llama3' not found`** — Pull it: `docker-compose exec ollama ollama pull llama3`

**Upload takes a long time / request times out** — Expected for large PDFs: there's no background task queue in this version, so the whole extract → chunk → embed → store pipeline runs inline before the response returns.

**`/ask` returns 404 "No matching content found"** — Nothing has been uploaded yet, or the `doc_id` filter doesn't match anything. Upload a document first, or omit `doc_id` to search everything.

**Answers cite the wrong part of the document, or reference unrelated sections** — This is the chunking model working as designed (see [The core limitation](#the-core-limitation) above), not a bug. A chunk has no concept of which section it came from, so similarity search can surface a chunk that only tangentially overlaps with the question's real subject.

**Connection errors to Qdrant** — `curl http://localhost:6333/collections`

**Scanned/image-only PDF returns almost no text** — There's no OCR fallback in this version; only PyMuPDF's native text layer is read.
