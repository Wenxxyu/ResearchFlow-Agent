from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.services.project_service import (
    ProjectAlreadyExistsError,
    create_project,
    delete_project,
    get_project,
    list_projects,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_endpoint(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    try:
        return create_project(db, payload)
    except ProjectAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[ProjectResponse])
def list_projects_endpoint(db: Session = Depends(get_db)) -> list[ProjectResponse]:
    return list_projects(db)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
) -> None:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    delete_project(db, project)
