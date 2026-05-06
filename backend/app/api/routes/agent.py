from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentStepResponse
from app.services.agent_service import AgentProjectNotFoundError, run_agent_chat

router = APIRouter(prefix="/projects/{project_id}/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
def agent_chat_endpoint(
    project_id: int,
    payload: AgentChatRequest,
    db: Session = Depends(get_db),
) -> AgentChatResponse:
    try:
        task = run_agent_chat(db, project_id, payload.message, payload.conversation_id)
    except AgentProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Agent model call failed or timed out. Check provider, base_url, model name, API key, "
                f"and network connectivity. Original error: {type(exc).__name__}: {exc}"
            ),
        ) from exc

    state = task.agent_state  # type: ignore[attr-defined]
    return AgentChatResponse(
        task_id=task.id,
        conversation_id=state["conversation_id"],
        task_type=state["task_type"],
        answer=state["answer"],
        log_analysis=state["log_analysis"],
        citations=state["citations"],
        steps=[
            AgentStepResponse(
                node_name=step["node_name"],
                input=step["input"],
                output=step["output"],
                latency_ms=step["latency_ms"],
            )
            for step in state["steps"]
        ],
        errors=state["errors"],
    )
