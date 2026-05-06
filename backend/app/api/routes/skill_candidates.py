from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.skill_candidate import SkillCandidate
from app.schemas.skill_candidate import SkillCandidateCreateRequest, SkillCandidateResponse
from app.skills.miner import (
    SkillCandidateAlreadyReviewedError,
    SkillCandidateNotAllowedError,
    SkillCandidateNotFoundError,
    SkillMiner,
    load_task_bundle,
)

router = APIRouter(tags=["skill-candidates"])


@router.post(
    "/tasks/{task_id}/skill-candidates",
    response_model=SkillCandidateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_skill_candidate_endpoint(
    task_id: int,
    payload: SkillCandidateCreateRequest | None = None,
    db: Session = Depends(get_db),
) -> SkillCandidateResponse:
    try:
        task, steps, memories = load_task_bundle(db, task_id)
        return SkillMiner().generate_candidate_skill(
            db=db,
            task=task,
            task_steps=steps,
            memories=memories,
            feedback=payload.feedback if payload else None,
        )
    except SkillCandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SkillCandidateNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/projects/{project_id}/skill-candidates", response_model=list[SkillCandidateResponse])
def list_skill_candidates_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
) -> list[SkillCandidateResponse]:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project not found: {project_id}")
    statement = (
        select(SkillCandidate)
        .where(SkillCandidate.project_id == project_id)
        .order_by(SkillCandidate.created_at.desc())
    )
    return list(db.scalars(statement).all())


@router.post("/skill-candidates/{candidate_id}/approve", response_model=SkillCandidateResponse)
def approve_skill_candidate_endpoint(
    candidate_id: int,
    db: Session = Depends(get_db),
) -> SkillCandidateResponse:
    try:
        return SkillMiner().approve_candidate_skill(db, candidate_id)
    except SkillCandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (SkillCandidateNotAllowedError, SkillCandidateAlreadyReviewedError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/skill-candidates/{candidate_id}/reject", response_model=SkillCandidateResponse)
def reject_skill_candidate_endpoint(
    candidate_id: int,
    db: Session = Depends(get_db),
) -> SkillCandidateResponse:
    try:
        return SkillMiner().reject_candidate_skill(db, candidate_id)
    except SkillCandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SkillCandidateAlreadyReviewedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
