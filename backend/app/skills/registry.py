from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.project import Project
from app.models.skill import Skill
from app.rag.embeddings import BaseEmbeddingProvider, MockEmbeddingProvider, cosine_similarity, tokenize_for_embedding
from app.skills.parser import ParsedSkill, parse_skill_file


@dataclass(frozen=True)
class SkillSearchResult:
    skill: Skill
    score: float
    tools: list[str]
    content_preview: str


class SkillNotFoundError(ValueError):
    pass


class SkillProjectNotFoundError(ValueError):
    pass


class SkillRegistry:
    def __init__(
        self,
        skill_root: str | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
    ) -> None:
        self.skill_root = Path(skill_root or get_settings().skill_dir)
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()

    def scan_skills(self, db: Session) -> list[Skill]:
        self.skill_root.mkdir(parents=True, exist_ok=True)
        registered: list[Skill] = []
        for skill_file in sorted(self.skill_root.glob("*/SKILL.md")):
            parsed = parse_skill_file(skill_file)
            registered.append(self.register_skill(db, parsed))
        return registered

    def register_skill(self, db: Session, parsed: ParsedSkill) -> Skill:
        statement = select(Skill).where(Skill.name == parsed.name)
        skill = db.scalar(statement)
        if skill is None:
            skill = Skill(
                name=parsed.name,
                description=parsed.description,
                trigger=parsed.trigger,
                path=parsed.path,
                status=parsed.status,
            )
            db.add(skill)
        else:
            skill.description = parsed.description
            skill.trigger = parsed.trigger
            skill.path = parsed.path
            skill.status = parsed.status
        db.commit()
        db.refresh(skill)
        return skill

    def search_skills(
        self,
        db: Session,
        project_id: int,
        query: str,
        top_k: int = 5,
        min_score: float = 0.15,
    ) -> list[SkillSearchResult]:
        if db.get(Project, project_id) is None:
            raise SkillProjectNotFoundError(f"Project not found: {project_id}")

        statement = select(Skill).where(Skill.status.in_(["draft", "active", "approved"])).order_by(Skill.name.asc())
        skills = list(db.scalars(statement).all())
        if not skills:
            return []

        query_vector = self.embedding_provider.embed_query(query)
        query_tokens = set(tokenize_for_embedding(query))
        results: list[SkillSearchResult] = []
        for skill in skills:
            parsed = self._parse_registered_skill(skill)
            text = f"{skill.name}\n{skill.description or ''}\n{skill.trigger or ''}\n{parsed.content}"
            skill_vector = self.embedding_provider.embed_query(text)
            semantic_score = max(0.0, cosine_similarity(query_vector, skill_vector))
            lexical_score = token_overlap_score(query_tokens, set(tokenize_for_embedding(text)))
            score = semantic_score * 0.7 + lexical_score * 0.3
            if score < min_score:
                continue
            results.append(
                SkillSearchResult(
                    skill=skill,
                    score=score,
                    tools=parsed.tools,
                    content_preview=parsed.content[:500],
                )
            )
        return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]

    def load_skill_content(self, db: Session, skill_id: int) -> tuple[Skill, ParsedSkill]:
        skill = db.get(Skill, skill_id)
        if skill is None:
            raise SkillNotFoundError(f"Skill not found: {skill_id}")
        return skill, self._parse_registered_skill(skill)

    def mark_skills_used(self, db: Session, skill_ids: list[int], success: bool = False) -> None:
        if not skill_ids:
            return
        statement = select(Skill).where(Skill.id.in_(skill_ids))
        skills = list(db.scalars(statement).all())
        for skill in skills:
            skill.usage_count += 1
            if success:
                skill.success_count += 1
        db.commit()

    def mark_skills_succeeded(self, db: Session, skill_ids: list[int]) -> None:
        if not skill_ids:
            return
        statement = select(Skill).where(Skill.id.in_(skill_ids))
        skills = list(db.scalars(statement).all())
        for skill in skills:
            skill.success_count += 1
        db.commit()

    def _parse_registered_skill(self, skill: Skill) -> ParsedSkill:
        return parse_skill_file(Path(skill.path) / "SKILL.md")


def token_overlap_score(query_tokens: set[str], document_tokens: set[str]) -> float:
    if not query_tokens or not document_tokens:
        return 0.0
    return len(query_tokens & document_tokens) / len(query_tokens)
