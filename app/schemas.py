from pydantic import BaseModel, HttpUrl, field_validator


class IngestRequest(BaseModel):
    repo_url: HttpUrl


class IngestResponse(BaseModel):
    message: str
    repo_name: str
    chunks_count: int
    files_count: int
    source: str  # "github" or "upload"


class QueryRequest(BaseModel):
    question: str
    repo_name: str

    @field_validator("question")
    @classmethod
    def question_min_length(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("question must be at least 3 characters")
        return v


class SourceItem(BaseModel):
    file_path: str
    chunk_preview: str
    similarity: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    question: str


class RepoInfo(BaseModel):
    repo_name: str
    document_count: int
    source: str


class HealthResponse(BaseModel):
    status: str
    version: str
