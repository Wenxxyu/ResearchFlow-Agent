from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SkillCandidateCreateRequest(BaseModel):
    feedback: str | None = None


class SkillCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    description: str
    content: str
    source_task_id: int
    status: str
    created_at: datetime
    updated_at: datetime
