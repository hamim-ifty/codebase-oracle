# 🔮 Codebase Oracle

AI-powered codebase onboarding assistant. Point it at any GitHub repo or upload a zip file and start asking natural language questions about the code.

---

## Architecture

```
 GitHub URL / Zip File
        │
        ▼
  ┌─────────────┐
  │   Loader    │  Clone repo or extract zip, read source files
  └──────┬──────┘
         │ Documents
         ▼
  ┌─────────────┐
  │   Chunker   │  Split into ~500-token chunks via RecursiveCharacterTextSplitter
  └──────┬──────┘
         │ Chunks
         ▼
  ┌─────────────────┐
  │ GeminiEmbedder  │  text-embedding-004 → 768-dim vectors
  └──────┬──────────┘
         │ Embeddings
         ▼
  ┌──────────────────────┐
  │ SupabaseVectorStore  │  PostgreSQL + pgvector (ivfflat index)
  └──────────────────────┘
         │
         ▼  (at query time)
  ┌──────────────┐
  │ RAG Pipeline │  embed question → similarity search → Gemini Flash
  └──────────────┘
         │
         ▼
     Answer + Sources
```

---

## Tech Stack

| Layer       | Technology                            |
|-------------|---------------------------------------|
| Backend     | Python 3.11+, FastAPI                 |
| LLM         | Google Gemini 2.0 Flash               |
| Embeddings  | Gemini text-embedding-004 (768-dim)   |
| Vector DB   | Supabase PostgreSQL + pgvector        |
| HTTP        | httpx                                 |
| Git cloning | gitpython                             |
| Chunking    | langchain-text-splitters              |
| Config      | pydantic-settings                     |

---

## Quick Start

### Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com) project
- A [Google AI Studio](https://aistudio.google.com) API key

### 1. Supabase Setup

Open your Supabase project → SQL Editor → run the contents of `supabase_setup.sql`.

### 2. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and fill in your keys
```

### 4. Start the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

---

## API Endpoints

| Method   | Path                  | Description                              |
|----------|-----------------------|------------------------------------------|
| `GET`    | `/health`             | Health check                             |
| `POST`   | `/ingest`             | Ingest a GitHub repository by URL        |
| `POST`   | `/ingest/upload`      | Ingest a local zip file upload           |
| `POST`   | `/query`              | Ask a question about an ingested repo    |
| `GET`    | `/repos`              | List all ingested repositories           |
| `DELETE` | `/repos/{repo_name}`  | Delete all data for a repository         |

---

## Example Usage

### Ingest a GitHub Repository

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/tiangolo/fastapi"}'
```

### Ingest a Zip File

```bash
curl -X POST http://localhost:8000/ingest/upload \
  -F "file=@my-project.zip" \
  -F "project_name=my-project"
```

### Ask a Question

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How does authentication work?", "repo_name": "fastapi"}'
```

### List Repositories

```bash
curl http://localhost:8000/repos
```

### Delete a Repository

```bash
curl -X DELETE http://localhost:8000/repos/fastapi
```

---

## Author

Built with Claude Code · [Report Issues](https://github.com/anthropics/claude-code/issues)
