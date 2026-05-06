import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.project import Project
from app.rag.parser import SUPPORTED_DOCUMENT_TYPES, UnsupportedDocumentTypeError, parse_document
from app.rag.splitter import RecursiveTextSplitter


class DocumentNotFoundError(ValueError):
    pass


class ProjectNotFoundError(ValueError):
    pass


class EmptyDocumentError(ValueError):
    pass


def upload_document(
    db: Session,
    project_id: int,
    upload_file: UploadFile,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> Document:
    project = db.get(Project, project_id)
    if project is None:
        raise ProjectNotFoundError(f"Project not found: {project_id}")

    original_filename = Path(upload_file.filename or "document").name
    suffix = Path(original_filename).suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_TYPES:
        raise UnsupportedDocumentTypeError(f"Unsupported document type: {suffix}")

    target_dir = Path(get_settings().upload_dir) / str(project_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}{suffix}"
    target_path = target_dir / stored_filename

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    document = Document(
        project_id=project_id,
        filename=original_filename,
        file_type=suffix.lstrip("."),
        file_path=str(target_path),
        status="processing",
        chunk_count=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        sections = parse_document(target_path)
        if not sections:
            raise EmptyDocumentError("Document contains no readable text")

        splitter = RecursiveTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunk_rows: list[Chunk] = []
        chunk_index = 0
        for section in sections:
            for piece in splitter.split_text(section.text):
                metadata = {
                    "document_id": document.id,
                    "project_id": project_id,
                    "filename": original_filename,
                    "file_type": document.file_type,
                    "page_number": section.page_number,
                    "chunk_index": chunk_index,
                    "start_index": piece.start_index,
                    "end_index": piece.end_index,
                }
                chunk_rows.append(
                    Chunk(
                        document_id=document.id,
                        project_id=project_id,
                        chunk_index=chunk_index,
                        content=piece.content,
                        metadata_json=json.dumps(metadata, ensure_ascii=False),
                    )
                )
                chunk_index += 1

        db.add_all(chunk_rows)
        document.status = "indexed"
        document.chunk_count = len(chunk_rows)
        db.commit()
        db.refresh(document)
        return document
    except Exception:
        document.status = "failed"
        document.chunk_count = 0
        db.commit()
        raise


def list_project_documents(db: Session, project_id: int) -> list[Document]:
    if db.get(Project, project_id) is None:
        raise ProjectNotFoundError(f"Project not found: {project_id}")
    statement = select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    return list(db.scalars(statement).all())


def get_document(db: Session, document_id: int) -> Document | None:
    return db.get(Document, document_id)


def get_required_document(db: Session, document_id: int) -> Document:
    document = get_document(db, document_id)
    if document is None:
        raise DocumentNotFoundError(f"Document not found: {document_id}")
    return document


def delete_document(db: Session, document: Document) -> None:
    file_path = Path(document.file_path)
    db.delete(document)
    db.commit()
    if file_path.exists() and file_path.is_file():
        file_path.unlink()


def list_document_chunks(db: Session, document_id: int) -> list[Chunk]:
    if get_document(db, document_id) is None:
        raise DocumentNotFoundError(f"Document not found: {document_id}")
    statement = select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index.asc())
    return list(db.scalars(statement).all())
