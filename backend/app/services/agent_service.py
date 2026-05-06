from sqlalchemy.orm import Session

from app.agent.workflow import run_agentic_rag_workflow
from app.models.project import Project
from app.models.task import Task


class AgentProjectNotFoundError(ValueError):
    pass


def run_agent_chat(db: Session, project_id: int, message: str, conversation_id: str | None = None) -> Task:
    if db.get(Project, project_id) is None:
        raise AgentProjectNotFoundError(f"Project not found: {project_id}")

    task = Task(
        project_id=project_id,
        task_type="pending",
        user_input=message,
        status="running",
        final_answer=None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    state = run_agentic_rag_workflow(
        db=db,
        task_id=task.id,
        project_id=project_id,
        user_input=message,
        conversation_id=conversation_id,
    )

    task.task_type = state["task_type"]
    task.final_answer = state["answer"]
    has_evidence = bool(state["retrieved_chunks"] or state["code_search_results"] or state["log_analysis"])
    task.status = "failed" if state["errors"] and not has_evidence else "completed"
    db.commit()
    db.refresh(task)
    task.agent_state = state  # type: ignore[attr-defined]
    return task
