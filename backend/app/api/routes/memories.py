from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.memory.manager import (
    InvalidMemoryTypeError,
    MemoryManager,
    MemoryNotFoundError,
    MemoryProjectNotFoundError,
)
from app.models.memory import Memory
from app.models.project import Project
from app.schemas.memory import MemoryCreate, MemoryResponse, MemorySearchRequest, MemorySearchResultResponse

router = APIRouter(tags=["memories"])


@router.post("/projects/{project_id}/memories", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
def create_memory_endpoint(
    project_id: int,
    payload: MemoryCreate,
    db: Session = Depends(get_db),
) -> MemoryResponse:
    try:
        return MemoryManager().write_memory(
            db=db,
            project_id=project_id,
            memory_type=payload.memory_type,
            content=payload.content,
            summary=payload.summary,
            importance=payload.importance,
            confidence=payload.confidence,
            source_task_id=payload.source_task_id,
            tags=payload.tags,
        )
    except MemoryProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidMemoryTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/projects/{project_id}/memories", response_model=list[MemoryResponse])
def list_memories_endpoint(
    project_id: int,
    memory_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[MemoryResponse]:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project not found: {project_id}")
    statement = select(Memory).where(Memory.project_id == project_id).order_by(Memory.created_at.desc())
    if memory_type:
        statement = statement.where(Memory.memory_type == memory_type)
    return list(db.scalars(statement).all())


@router.post("/projects/{project_id}/memories/search", response_model=list[MemorySearchResultResponse])
def search_memories_endpoint(
    project_id: int,
    payload: MemorySearchRequest,
    db: Session = Depends(get_db),
) -> list[MemorySearchResultResponse]:
    try:
        results = MemoryManager().search_memory(
            db=db,
            project_id=project_id,
            query=payload.query,
            top_k=payload.top_k,
            memory_type=payload.memory_type,
            min_confidence=payload.min_confidence,
        )
    except MemoryProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidMemoryTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [
        MemorySearchResultResponse(
            memory=result.memory,
            score=result.score,
            similarity=result.similarity,
            recency=result.recency,
            type_match=result.type_match,
        )
        for result in results
    ]


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory_endpoint(memory_id: int, db: Session = Depends(get_db)) -> None:
    try:
        MemoryManager().delete_memory(db, memory_id)
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
