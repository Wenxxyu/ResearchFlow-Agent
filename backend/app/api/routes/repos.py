from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.repo.manager import RepoError, import_local_repo, import_zip_repo, load_repo_index, read_repo_file, search_repo
from app.schemas.repo import RepoFileResponse, RepoImportResponse, RepoSearchRequest, RepoSearchResultResponse, RepoTreeResponse

router = APIRouter(prefix="/projects/{project_id}/repos", tags=["repos"])


@router.post("/upload", response_model=RepoImportResponse)
def upload_repo_endpoint(
    project_id: int,
    file: UploadFile | None = File(default=None),
    local_path: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> RepoImportResponse:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project not found: {project_id}")
    try:
        if file is not None:
            if not (file.filename or "").lower().endswith(".zip"):
                raise RepoError("Only zip repositories are supported for upload")
            index = import_zip_repo(project_id, file)
        elif local_path:
            index = import_local_repo(project_id, local_path)
        else:
            raise RepoError("Provide either a zip file or local_path")
    except RepoError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RepoImportResponse(
        project_id=project_id,
        file_count=len(index["files"]),
        symbol_count=len(index["symbols"]),
        readme_summary=index["readme_summary"],
    )


@router.get("/tree", response_model=RepoTreeResponse)
def repo_tree_endpoint(project_id: int) -> RepoTreeResponse:
    try:
        index = load_repo_index(project_id)
    except RepoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RepoTreeResponse(**index)


@router.post("/search", response_model=list[RepoSearchResultResponse])
def repo_search_endpoint(project_id: int, payload: RepoSearchRequest) -> list[RepoSearchResultResponse]:
    try:
        return search_repo(project_id, payload.query, payload.top_k)
    except RepoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/files", response_model=RepoFileResponse)
def repo_file_endpoint(project_id: int, path: str = Query(...)) -> RepoFileResponse:
    try:
        return RepoFileResponse(**read_repo_file(project_id, path))
    except RepoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
