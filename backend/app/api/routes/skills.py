from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.skill import Skill
from app.schemas.skill import (
    SkillDetailResponse,
    SkillResponse,
    SkillScanResponse,
    SkillSearchRequest,
    SkillSearchResultResponse,
)
from app.skills.registry import SkillNotFoundError, SkillProjectNotFoundError, SkillRegistry

router = APIRouter(tags=["skills"])


@router.get("/skills", response_model=list[SkillResponse])
def list_skills_endpoint(db: Session = Depends(get_db)) -> list[SkillResponse]:
    statement = select(Skill).order_by(Skill.name.asc())
    return list(db.scalars(statement).all())


@router.get("/skills/{skill_id}", response_model=SkillDetailResponse)
def get_skill_endpoint(skill_id: int, db: Session = Depends(get_db)) -> SkillDetailResponse:
    try:
        skill, parsed = SkillRegistry().load_skill_content(db, skill_id)
    except SkillNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SkillDetailResponse(
        **SkillResponse.model_validate(skill).model_dump(),
        tools=parsed.tools,
        content=parsed.content,
    )


@router.post("/skills/scan", response_model=SkillScanResponse)
def scan_skills_endpoint(db: Session = Depends(get_db)) -> SkillScanResponse:
    skills = SkillRegistry().scan_skills(db)
    return SkillScanResponse(scanned_count=len(skills), skills=skills)


@router.post("/projects/{project_id}/skills/search", response_model=list[SkillSearchResultResponse])
def search_skills_endpoint(
    project_id: int,
    payload: SkillSearchRequest,
    db: Session = Depends(get_db),
) -> list[SkillSearchResultResponse]:
    try:
        results = SkillRegistry().search_skills(
            db=db,
            project_id=project_id,
            query=payload.query,
            top_k=payload.top_k,
            min_score=payload.min_score,
        )
    except SkillProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [
        SkillSearchResultResponse(
            skill=result.skill,
            score=result.score,
            tools=result.tools,
            content_preview=result.content_preview,
        )
        for result in results
    ]
