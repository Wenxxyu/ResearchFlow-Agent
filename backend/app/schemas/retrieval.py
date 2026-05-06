from pydantic import BaseModel, Field


class BuildIndexResponse(BaseModel):
    project_id: int
    chunk_count: int
    vector_count: int
    bm25_count: int
    status: str


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    task_type: str = Field(default="general_qa")


class RetrievalResultResponse(BaseModel):
    chunk_id: int
    document_id: int
    project_id: int
    chunk_index: int
    source: str
    content: str
    filename: str
    file_type: str
    score: float
    score_breakdown: dict
    vector_score: float
    bm25_score: float
    metadata: dict


class RetrieveResponse(BaseModel):
    project_id: int
    query: str
    top_k: int
    results: list[RetrievalResultResponse]
