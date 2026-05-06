from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    trigger: str | None
    path: str
    status: str
    usage_count: int
    success_count: int
    created_from_task_id: int | None
    created_at: datetime
    updated_at: datetime


class SkillDetailResponse(SkillResponse):
    tools: list[str]
    content: str


class SkillScanResponse(BaseModel):
    scanned_count: int
    skills: list[SkillResponse]


class SkillSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    min_score: float = Field(default=0.15, ge=0.0, le=1.0)


class SkillSearchResultResponse(BaseModel):
    skill: SkillResponse
    score: float
    tools: list[str]
    content_preview: str
