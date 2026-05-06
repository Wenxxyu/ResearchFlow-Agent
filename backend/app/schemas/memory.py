from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemoryCreate(BaseModel):
    memory_type: str
    content: str = Field(min_length=1)
    summary: str | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    source_task_id: int | None = None
    tags: list[str] = Field(default_factory=list)


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    memory_type: str | None = None
    min_confidence: float = Field(default=0.35, ge=0.0, le=1.0)


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    memory_type: str
    content: str
    summary: str | None
    importance: float
    confidence: float
    source_task_id: int | None
    tags_json: str | None
    created_at: datetime
    last_accessed_at: datetime | None


class MemorySearchResultResponse(BaseModel):
    memory: MemoryResponse
    score: float
    similarity: float
    recency: float
    type_match: float
