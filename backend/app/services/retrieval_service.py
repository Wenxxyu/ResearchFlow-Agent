from sqlalchemy.orm import Session

from app.rag.retriever import HybridRetriever, RetrievalResult


def build_project_index(db: Session, project_id: int) -> dict[str, int]:
    return HybridRetriever().build_project_index(db, project_id)


def retrieve_project_chunks(
    db: Session,
    project_id: int,
    query: str,
    top_k: int,
    task_type: str = "general_qa",
) -> list[RetrievalResult]:
    return HybridRetriever().retrieve(db, project_id, query, top_k, task_type=task_type)
