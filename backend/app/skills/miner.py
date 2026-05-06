import re
from pathlib import Path
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.memory import Memory
from app.models.skill_candidate import SkillCandidate
from app.models.task import Task
from app.models.task_step import TaskStep
from app.skills.registry import SkillRegistry


class SkillCandidateNotFoundError(ValueError):
    pass


class SkillCandidateNotAllowedError(ValueError):
    pass


class SkillCandidateAlreadyReviewedError(ValueError):
    pass


class SkillMiner:
    reusable_nodes = {
        "retrieval_node",
        "skill_recall_node",
        "memory_recall_node",
        "answer_node",
        "citation_verify_node",
    }
    eligible_task_types = {"log_debug", "repo_qa", "paper_qa"}

    def should_create_skill(
        self,
        task: Task,
        task_steps: list[TaskStep],
        feedback: str | None = None,
    ) -> bool:
        if task.status != "completed":
            return False
        if len(task_steps) < 3:
            return False
        has_reusable_step = any(step.node_name in self.reusable_nodes or "tool" in step.node_name for step in task_steps)
        if not has_reusable_step:
            return False
        positive_feedback = (feedback or "").lower() == "positive"
        return positive_feedback or task.task_type in self.eligible_task_types

    def generate_candidate_skill(
        self,
        db: Session,
        task: Task,
        task_steps: list[TaskStep],
        memories: list[Memory] | None = None,
        feedback: str | None = None,
    ) -> SkillCandidate:
        if not self.should_create_skill(task, task_steps, feedback):
            raise SkillCandidateNotAllowedError("Task does not meet candidate skill generation rules")

        name = make_candidate_skill_name(task)
        description = f"Reusable workflow distilled from task {task.id}: {task.task_type}."
        content = render_candidate_skill_markdown(task, task_steps, memories or [], name, description)

        candidate = SkillCandidate(
            project_id=task.project_id,
            name=name,
            description=description,
            content=content,
            source_task_id=task.id,
            status="candidate",
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

    def approve_candidate_skill(self, db: Session, candidate_id: int) -> SkillCandidate:
        candidate = self._get_candidate(db, candidate_id)
        if candidate.status != "candidate":
            raise SkillCandidateAlreadyReviewedError(f"Candidate already reviewed: {candidate.status}")

        skill_dir = safe_skill_directory(candidate.name)
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "references").mkdir(exist_ok=True)
        (skill_dir / "assets").mkdir(exist_ok=True)

        skill_content = candidate.content.replace("status: candidate", "status: active", 1)
        (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        candidate.status = "approved"
        db.commit()
        db.refresh(candidate)
        SkillRegistry().scan_skills(db)
        return candidate

    def reject_candidate_skill(self, db: Session, candidate_id: int) -> SkillCandidate:
        candidate = self._get_candidate(db, candidate_id)
        if candidate.status != "candidate":
            raise SkillCandidateAlreadyReviewedError(f"Candidate already reviewed: {candidate.status}")
        candidate.status = "rejected"
        db.commit()
        db.refresh(candidate)
        return candidate

    def _get_candidate(self, db: Session, candidate_id: int) -> SkillCandidate:
        candidate = db.get(SkillCandidate, candidate_id)
        if candidate is None:
            raise SkillCandidateNotFoundError(f"Skill candidate not found: {candidate_id}")
        return candidate


def load_task_bundle(db: Session, task_id: int) -> tuple[Task, list[TaskStep], list[Memory]]:
    task = db.get(Task, task_id)
    if task is None:
        raise SkillCandidateNotFoundError(f"Task not found: {task_id}")
    steps = list(db.scalars(select(TaskStep).where(TaskStep.task_id == task_id).order_by(TaskStep.id.asc())).all())
    memories = list(db.scalars(select(Memory).where(Memory.source_task_id == task_id).order_by(Memory.id.asc())).all())
    return task, steps, memories


def make_candidate_skill_name(task: Task) -> str:
    raw = f"{task.task_type}_task_{task.id}"
    return sanitize_skill_name(raw)


def sanitize_skill_name(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower()).strip("_")
    if not normalized:
        raise SkillCandidateNotAllowedError("Skill name is empty after sanitization")
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", normalized):
        raise SkillCandidateNotAllowedError("Invalid skill name")
    return normalized[:96]


def safe_skill_directory(skill_name: str) -> Path:
    safe_name = sanitize_skill_name(skill_name)
    root = Path(get_settings().skill_dir).resolve()
    target = (root / safe_name).resolve()
    if root != target and root not in target.parents:
        raise SkillCandidateNotAllowedError("Skill path escapes skill root")
    return target


def render_candidate_skill_markdown(
    task: Task,
    task_steps: list[TaskStep],
    memories: list[Memory],
    name: str,
    description: str,
) -> str:
    step_names = [step.node_name for step in task_steps]
    memory_summaries = [memory.summary or memory.content[:160] for memory in memories[:5]]
    trigger = make_trigger(task)
    steps = "\n".join(f"{index + 1}. {step_name}" for index, step_name in enumerate(step_names[:10]))
    memories_block = "\n".join(f"- {summary}" for summary in memory_summaries) or "- No related memories captured."
    return f"""---
name: {name}
description: {yaml_quote(description)}
tools:
  - hybrid_retriever
  - memory_manager
  - skill_registry
status: candidate
trigger: {yaml_quote(trigger)}
---

# {name}

## Purpose

{description}

## Trigger

{trigger}

## Reusable Steps

{steps}

## Source Task

- Task ID: {task.id}
- Task Type: {task.task_type}
- User Input: {task.user_input}
- Status: {task.status}

## Lessons And Memories

{memories_block}

## Safety

This candidate skill does not include executable scripts. Review and approve before activation.
"""


def make_trigger(task: Task) -> str:
    if task.task_type == "log_debug":
        return "training log, runtime error, CUDA OOM, traceback, failed experiment"
    if task.task_type == "repo_qa":
        return "repository understanding, code question, function explanation, traceback location"
    if task.task_type == "paper_qa":
        return "paper reading, cited QA, method summary, experiment analysis"
    return f"similar task to: {task.user_input[:120]}"


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
