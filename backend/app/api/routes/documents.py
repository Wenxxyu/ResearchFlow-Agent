from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.rag.parser import UnsupportedDocumentTypeError
from app.schemas.chunk import ChunkResponse
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.services.document_service import (
    DocumentNotFoundError,
    EmptyDocumentError,
    ProjectNotFoundError,
    delete_document,
    get_required_document,
    list_document_chunks,
    list_project_documents,
    upload_document,
)

router = APIRouter(tags=["documents"])


@router.post(
    "/projects/{project_id}/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_project_document(
    project_id: int,
    file: UploadFile = File(...),
    chunk_size: int = Form(800),
    chunk_overlap: int = Form(120),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    try:
        return upload_document(
            db=db,
            project_id=project_id,
            upload_file=file,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/projects/{project_id}/documents", response_model=list[DocumentResponse])
def list_documents_for_project(
    project_id: int,
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    try:
        return list_project_documents(db, project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    try:
        return get_required_document(db, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
) -> None:
    try:
        document = get_required_document(db, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    delete_document(db, document)


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkResponse])
def list_chunks_for_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> list[ChunkResponse]:
    try:
        return list_document_chunks(db, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
