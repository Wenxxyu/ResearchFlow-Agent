from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.rag.retriever import ProjectNotFoundForRetrievalError, RetrievalIndexNotFoundError
from app.schemas.retrieval import BuildIndexResponse, RetrievalResultResponse, RetrieveRequest, RetrieveResponse
from app.services.retrieval_service import build_project_index, retrieve_project_chunks

router = APIRouter(prefix="/projects/{project_id}", tags=["retrieval"])


@router.post("/index/build", response_model=BuildIndexResponse)
def build_index_endpoint(project_id: int, db: Session = Depends(get_db)) -> BuildIndexResponse:
    try:
        result = build_project_index(db, project_id)
    except ProjectNotFoundForRetrievalError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BuildIndexResponse(project_id=project_id, status="built", **result)


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve_endpoint(
    project_id: int,
    payload: RetrieveRequest,
    db: Session = Depends(get_db),
) -> RetrieveResponse:
    try:
        results = retrieve_project_chunks(db, project_id, payload.query, payload.top_k, payload.task_type)
    except ProjectNotFoundForRetrievalError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RetrievalIndexNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return RetrieveResponse(
        project_id=project_id,
        query=payload.query,
        top_k=payload.top_k,
        results=[
            RetrievalResultResponse(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                project_id=result.project_id,
                chunk_index=result.chunk_index,
                source=result.source,
                content=result.content,
                filename=result.filename,
                file_type=result.file_type,
                score=result.score,
                score_breakdown=result.score_breakdown,
                vector_score=result.vector_score,
                bm25_score=result.bm25_score,
                metadata=result.metadata,
            )
            for result in results
        ],
    )
