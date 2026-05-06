from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=128)


class AgentStepResponse(BaseModel):
    node_name: str
    input: dict
    output: dict
    latency_ms: int


class AgentChatResponse(BaseModel):
    task_id: int
    conversation_id: str | None = None
    task_type: str
    answer: str
    log_analysis: dict | None = None
    citations: list[str]
    steps: list[AgentStepResponse]
    errors: list[str]
