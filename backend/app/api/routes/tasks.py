from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.task import Task
from app.models.task_step import TaskStep
from app.schemas.task import TaskResponse, TaskStepResponse

router = APIRouter(tags=["tasks"])


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
def list_project_tasks_endpoint(project_id: int, db: Session = Depends(get_db)) -> list[TaskResponse]:
    statement = select(Task).where(Task.project_id == project_id).order_by(Task.created_at.desc())
    return list(db.scalars(statement).all())


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task_endpoint(task_id: int, db: Session = Depends(get_db)) -> TaskResponse:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task not found: {task_id}")
    return task


@router.get("/tasks/{task_id}/steps", response_model=list[TaskStepResponse])
def list_task_steps_endpoint(task_id: int, db: Session = Depends(get_db)) -> list[TaskStepResponse]:
    if db.get(Task, task_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task not found: {task_id}")
    statement = select(TaskStep).where(TaskStep.task_id == task_id).order_by(TaskStep.id.asc())
    return list(db.scalars(statement).all())
