import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory import Memory
from app.models.project import Project
from app.models.task import Task
from app.rag.embeddings import BaseEmbeddingProvider, MockEmbeddingProvider, cosine_similarity

MEMORY_TYPES = {"working", "episodic", "semantic", "user_profile", "reflection", "skill"}


class InvalidMemoryTypeError(ValueError):
    pass


class MemoryNotFoundError(ValueError):
    pass


class MemoryProjectNotFoundError(ValueError):
    pass


@dataclass(frozen=True)
class MemorySearchResult:
    memory: Memory
    score: float
    similarity: float
    recency: float
    type_match: float


class MemoryManager:
    def __init__(self, embedding_provider: BaseEmbeddingProvider | None = None) -> None:
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()

    def write_memory(
        self,
        db: Session,
        project_id: int,
        memory_type: str,
        content: str,
        summary: str | None = None,
        importance: float = 0.5,
        confidence: float = 0.7,
        source_task_id: int | None = None,
        tags: list[str] | None = None,
    ) -> Memory:
        self._validate_project(db, project_id)
        self._validate_memory_type(memory_type)
        memory = Memory(
            project_id=project_id,
            memory_type=memory_type,
            content=content,
            summary=summary,
            importance=clamp(importance),
            confidence=clamp(confidence),
            source_task_id=source_task_id,
            tags_json=json.dumps(tags or [], ensure_ascii=False),
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    def search_memory(
        self,
        db: Session,
        project_id: int,
        query: str,
        top_k: int = 5,
        memory_type: str | None = None,
        min_confidence: float = 0.35,
    ) -> list[MemorySearchResult]:
        self._validate_project(db, project_id)
        if memory_type is not None:
            self._validate_memory_type(memory_type)

        statement = select(Memory).where(
            Memory.project_id == project_id,
            Memory.confidence >= min_confidence,
        )
        memories = list(db.scalars(statement).all())
        if not memories:
            return []

        query_vector = self.embedding_provider.embed_query(query)
        results: list[MemorySearchResult] = []
        for memory in memories:
            memory_text = f"{memory.summary or ''}\n{memory.content}"
            memory_vector = self.embedding_provider.embed_query(memory_text)
            similarity = max(0.0, cosine_similarity(query_vector, memory_vector))
            recency = calculate_recency(memory.last_accessed_at or memory.created_at)
            type_match = 1.0 if memory_type is None or memory.memory_type == memory_type else 0.0
            score = similarity * 0.5 + memory.importance * 0.2 + recency * 0.2 + type_match * 0.1
            results.append(
                MemorySearchResult(
                    memory=memory,
                    score=score,
                    similarity=similarity,
                    recency=recency,
                    type_match=type_match,
                )
            )

        ranked = sorted(results, key=lambda result: result.score, reverse=True)[:top_k]
        for result in ranked:
            self.update_memory_access(db, result.memory)
        return ranked

    def update_memory_access(self, db: Session, memory: Memory) -> Memory:
        memory.last_accessed_at = datetime.utcnow()
        db.commit()
        db.refresh(memory)
        return memory

    def summarize_task_to_memory(
        self,
        db: Session,
        task: Task,
        steps: list[dict],
        errors: list[str] | None = None,
    ) -> list[Memory]:
        errors = errors or []
        step_names = [str(step.get("node_name", "")) for step in steps]
        memories = [
            self.write_memory(
                db=db,
                project_id=task.project_id,
                memory_type="episodic",
                content=(
                    f"Task {task.id} handled input: {task.user_input}\n"
                    f"Task type: {task.task_type}\n"
                    f"Status: {task.status}\n"
                    f"Steps: {', '.join(step_names)}\n"
                    f"Answer preview: {(task.final_answer or '')[:500]}"
                ),
                summary=f"Task {task.id}: {task.task_type} completed with {len(step_names)} steps.",
                importance=0.55,
                confidence=0.75 if not errors else 0.55,
                source_task_id=task.id,
                tags=["task", task.task_type],
            )
        ]
        if errors:
            memories.append(
                self.write_memory(
                    db=db,
                    project_id=task.project_id,
                    memory_type="reflection",
                    content=(
                        f"Task {task.id} produced errors: {'; '.join(errors)}\n"
                        "Next time, check retrieval index availability, evidence coverage, and citation validity first."
                    ),
                    summary=f"Reflection for task {task.id}: errors occurred during Agent workflow.",
                    importance=0.7,
                    confidence=0.65,
                    source_task_id=task.id,
                    tags=["reflection", "error", task.task_type],
                )
            )
        return memories

    def write_skill_memory(
        self,
        db: Session,
        project_id: int,
        skill_id: int,
        skill_name: str,
        task_type: str,
        user_input: str,
        outcome: str,
        source_task_id: int | None = None,
        answer_preview: str | None = None,
    ) -> Memory:
        normalized_outcome = outcome if outcome in {"success", "failure", "unknown"} else "unknown"
        importance = 0.68 if normalized_outcome == "success" else 0.52
        confidence = 0.78 if normalized_outcome == "success" else 0.58
        return self.write_memory(
            db=db,
            project_id=project_id,
            memory_type="skill",
            content=(
                f"Skill usage memory\n"
                f"Skill: {skill_name} (id={skill_id})\n"
                f"Task type: {task_type}\n"
                f"Outcome: {normalized_outcome}\n"
                f"User input: {user_input}\n"
                f"Answer preview: {(answer_preview or '')[:700]}"
            ),
            summary=f"Skill {skill_name} was used for {task_type} with outcome={normalized_outcome}.",
            importance=importance,
            confidence=confidence,
            source_task_id=source_task_id,
            tags=["skill", f"skill:{skill_name}", f"skill_id:{skill_id}", task_type, normalized_outcome],
        )

    def search_skill_memory(
        self,
        db: Session,
        project_id: int,
        query: str,
        top_k: int = 3,
        min_confidence: float = 0.35,
    ) -> list[MemorySearchResult]:
        results = self.search_memory(
            db=db,
            project_id=project_id,
            query=query,
            top_k=max(top_k * 3, top_k),
            memory_type="skill",
            min_confidence=min_confidence,
        )
        return [result for result in results if result.memory.memory_type == "skill"][:top_k]

    def get_memory(self, db: Session, memory_id: int) -> Memory:
        memory = db.get(Memory, memory_id)
        if memory is None:
            raise MemoryNotFoundError(f"Memory not found: {memory_id}")
        return memory

    def delete_memory(self, db: Session, memory_id: int) -> None:
        memory = self.get_memory(db, memory_id)
        db.delete(memory)
        db.commit()

    def _validate_project(self, db: Session, project_id: int) -> None:
        if db.get(Project, project_id) is None:
            raise MemoryProjectNotFoundError(f"Project not found: {project_id}")

    def _validate_memory_type(self, memory_type: str) -> None:
        if memory_type not in MEMORY_TYPES:
            raise InvalidMemoryTypeError(f"Invalid memory_type: {memory_type}")


def calculate_recency(timestamp: datetime | None) -> float:
    if timestamp is None:
        return 0.0
    age_days = max((datetime.utcnow() - timestamp).total_seconds() / 86400, 0.0)
    return 1.0 / (1.0 + age_days / 30.0)


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return min(max(value, lower), upper)
