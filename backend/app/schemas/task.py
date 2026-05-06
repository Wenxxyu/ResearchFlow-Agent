from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    task_type: str
    user_input: str
    status: str
    final_answer: str | None
    created_at: datetime
    updated_at: datetime


class TaskStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    node_name: str
    input_json: str | None
    output_json: str | None
    latency_ms: int | None
    created_at: datetime
