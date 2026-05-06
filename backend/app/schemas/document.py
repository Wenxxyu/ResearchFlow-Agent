from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    filename: str
    file_type: str
    file_path: str
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(DocumentResponse):
    pass
