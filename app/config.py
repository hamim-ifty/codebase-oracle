from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str

    CLONE_DIR: str = "./temp_repos"
    MAX_FILE_SIZE_KB: int = 100
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    MAX_UPLOAD_SIZE_MB: int = 50

    SUPPORTED_EXTENSIONS: list[str] = [
        ".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".txt",
        ".yaml", ".yml", ".json", ".toml", ".html", ".css",
        ".java", ".go", ".rs", ".sh", ".sql",
    ]

    SKIP_DIRS: list[str] = [
        "node_modules", ".git", "__pycache__", "venv",
        "dist", "build", ".next", "coverage",
    ]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
