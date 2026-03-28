import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from app.chunker import Chunker
from app.config import get_settings
from app.embeddings import GeminiEmbedder
from app.loader import RepoLoader
from app.rag import RAGPipeline
from app.schemas import (
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    RepoInfo,
    SourceItem,
)
from app.vector_store import SupabaseVectorStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Codebase Oracle is ready")
    yield


app = FastAPI(title="Codebase Oracle API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", version="1.0.0")


@app.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    repo_url = str(request.repo_url)
    print(f"[main] Ingesting GitHub repo: {repo_url}")

    try:
        loader = RepoLoader()
        documents = loader.load_from_url(repo_url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to load repository: {e}")

    if not documents:
        raise HTTPException(status_code=422, detail="No supported files found in the repository.")

    repo_name = documents[0].metadata["repo_name"]
    files_count = len(documents)

    try:
        chunker = Chunker()
        chunks = chunker.chunk_documents(documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to chunk documents: {e}")

    try:
        embedder = GeminiEmbedder()
        texts = [c.content for c in chunks]
        embeddings = embedder.embed_batch(texts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {e}")

    try:
        vector_store = SupabaseVectorStore()
        vector_store.store_documents(chunks, embeddings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store embeddings: {e}")

    print(f"[main] Ingestion complete: {files_count} files, {len(chunks)} chunks")
    return IngestResponse(
        message="Repository ingested successfully.",
        repo_name=repo_name,
        chunks_count=len(chunks),
        files_count=files_count,
        source="github",
    )


@app.post("/ingest/upload", response_model=IngestResponse)
async def ingest_upload(
    file: UploadFile,
    project_name: str = Form(None),
):
    settings = get_settings()

    # Validate file type
    filename = file.filename or ""
    content_type = file.content_type or ""
    if not filename.endswith(".zip") and content_type not in ("application/zip", "application/x-zip-compressed"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted.")

    # Read and validate size
    data = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    # Derive project name
    if not project_name:
        project_name = Path(filename).stem

    # Save to temp path
    os.makedirs(settings.CLONE_DIR, exist_ok=True)
    temp_zip = Path(settings.CLONE_DIR) / f"upload_{project_name}.zip"
    print(f"[main] Saving uploaded zip to {temp_zip}")

    try:
        temp_zip.write_bytes(data)

        import zipfile
        if not zipfile.is_zipfile(temp_zip):
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid zip archive.")

        loader = RepoLoader()
        try:
            documents = loader.load_from_zip(temp_zip, project_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to load zip: {e}")
    finally:
        if temp_zip.exists():
            temp_zip.unlink()
            print(f"[main] Removed temp zip {temp_zip}")

    if not documents:
        raise HTTPException(status_code=422, detail="No supported files found in the zip.")

    files_count = len(documents)

    try:
        chunker = Chunker()
        chunks = chunker.chunk_documents(documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to chunk documents: {e}")

    try:
        embedder = GeminiEmbedder()
        texts = [c.content for c in chunks]
        embeddings = embedder.embed_batch(texts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {e}")

    try:
        vector_store = SupabaseVectorStore()
        vector_store.store_documents(chunks, embeddings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store embeddings: {e}")

    print(f"[main] Upload ingestion complete: {files_count} files, {len(chunks)} chunks")
    return IngestResponse(
        message="Zip archive ingested successfully.",
        repo_name=project_name,
        chunks_count=len(chunks),
        files_count=files_count,
        source="upload",
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    print(f"[main] Query: {request.question!r} on repo '{request.repo_name}'")
    try:
        pipeline = RAGPipeline()
        result = pipeline.query(request.question, request.repo_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceItem(**s) for s in result["sources"]],
        question=result["question"],
    )


@app.get("/repos", response_model=list[RepoInfo])
async def list_repos():
    try:
        vector_store = SupabaseVectorStore()
        repos = vector_store.list_repos()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list repos: {e}")
    return [RepoInfo(**r) for r in repos]


@app.delete("/repos/{repo_name}")
async def delete_repo(repo_name: str):
    try:
        vector_store = SupabaseVectorStore()
        deleted = vector_store.delete_repo(repo_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete repo: {e}")
    return {"message": f"Deleted {deleted} documents for repo '{repo_name}'.", "repo_name": repo_name}
