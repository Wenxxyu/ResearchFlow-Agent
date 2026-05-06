from pydantic import BaseModel, Field


class RepoImportResponse(BaseModel):
    project_id: int
    file_count: int
    symbol_count: int
    readme_summary: str


class RepoTreeResponse(BaseModel):
    project_id: int
    tree: list[dict]
    files: list[dict]
    symbols: list[dict]
    readme_summary: str


class RepoSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)


class RepoSearchResultResponse(BaseModel):
    path: str
    line_start: int
    line_end: int
    snippet: str
    match_type: str
    symbol_name: str | None = None


class RepoFileResponse(BaseModel):
    path: str
    content: str
    truncated: bool
