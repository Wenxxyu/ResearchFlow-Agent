import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    app_name: str = "ResearchFlow-Agent"
    version: str = "0.1.0"
    api_prefix: str = "/api"
    debug: bool = True
    database_url: str = os.getenv("RESEARCHFLOW_DATABASE_URL", "sqlite:///./data/researchflow.sqlite3")
    upload_dir: str = os.getenv("RESEARCHFLOW_UPLOAD_DIR", "data/uploads")
    repo_dir: str = os.getenv("RESEARCHFLOW_REPO_DIR", "data/repos")
    skill_dir: str = os.getenv("RESEARCHFLOW_SKILL_DIR", "skills")
    llm_provider: str = os.getenv("RESEARCHFLOW_LLM_PROVIDER", "mock")
    llm_api_key: str | None = os.getenv("RESEARCHFLOW_LLM_API_KEY") or None
    llm_base_url: str | None = os.getenv("RESEARCHFLOW_LLM_BASE_URL") or None
    llm_model: str = os.getenv("RESEARCHFLOW_LLM_MODEL", "gpt-4.1-mini")
    llm_timeout_seconds: float = float(os.getenv("RESEARCHFLOW_LLM_TIMEOUT_SECONDS", "30"))
    embedding_provider: str = os.getenv("RESEARCHFLOW_EMBEDDING_PROVIDER", "mock")
    embedding_api_key: str | None = os.getenv("RESEARCHFLOW_EMBEDDING_API_KEY") or None
    embedding_base_url: str | None = os.getenv("RESEARCHFLOW_EMBEDDING_BASE_URL") or None
    embedding_model: str = os.getenv("RESEARCHFLOW_EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dimension: int = int(os.getenv("RESEARCHFLOW_EMBEDDING_DIMENSION", "1536"))
    embedding_batch_size: int = int(os.getenv("RESEARCHFLOW_EMBEDDING_BATCH_SIZE", "10"))
    embedding_timeout_seconds: float = float(os.getenv("RESEARCHFLOW_EMBEDDING_TIMEOUT_SECONDS", "60"))
    reranker_provider: str = os.getenv("RESEARCHFLOW_RERANKER_PROVIDER", "noop")
    reranker_api_key: str | None = os.getenv("RESEARCHFLOW_RERANKER_API_KEY") or None
    reranker_base_url: str | None = os.getenv("RESEARCHFLOW_RERANKER_BASE_URL") or None
    reranker_model: str = os.getenv("RESEARCHFLOW_RERANKER_MODEL", "gpt-4.1-mini")
    reranker_timeout_seconds: float = float(os.getenv("RESEARCHFLOW_RERANKER_TIMEOUT_SECONDS", "30"))
    backend_cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @property
    def sqlite_path(self) -> Path | None:
        if not self.database_url.startswith("sqlite:///"):
            return None
        raw_path = self.database_url.replace("sqlite:///", "", 1)
        return Path(raw_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
