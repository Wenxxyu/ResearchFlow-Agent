from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate


class ProjectAlreadyExistsError(ValueError):
    pass


def create_project(db: Session, payload: ProjectCreate) -> Project:
    project = Project(name=payload.name, description=payload.description)
    db.add(project)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ProjectAlreadyExistsError(f"Project name already exists: {payload.name}") from exc
    db.refresh(project)
    return project


def list_projects(db: Session) -> list[Project]:
    statement = select(Project).order_by(Project.created_at.desc())
    return list(db.scalars(statement).all())


def get_project(db: Session, project_id: int) -> Project | None:
    return db.get(Project, project_id)


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()
