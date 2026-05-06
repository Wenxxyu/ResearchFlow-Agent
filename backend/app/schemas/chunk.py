from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    project_id: int
    chunk_index: int
    content: str
    metadata_json: str | None
    created_at: datetime
