import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.llm.provider import ChatMessage, OpenAICompatibleLLMProvider
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.project import Project
from app.rag.bm25_store import BM25IndexNotFoundError, BM25Store, get_bm25_store
from app.rag.vector_store import FaissVectorStore, VectorIndexNotFoundError, get_vector_store


@dataclass(frozen=True)
class RetrieverHit:
    chunk_id: int
    source: str
    raw_score: float
    normalized_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: int
    document_id: int
    project_id: int
    chunk_index: int
    source: str
    content: str
    filename: str
    file_type: str
    score: float
    score_breakdown: dict[str, float]
    metadata: dict[str, Any]

    @property
    def vector_score(self) -> float:
        return self.score_breakdown.get("vector_raw", 0.0)

    @property
    def bm25_score(self) -> float:
        return self.score_breakdown.get("bm25_raw", 0.0)


class ProjectNotFoundForRetrievalError(ValueError):
    pass


class RetrievalIndexNotFoundError(FileNotFoundError):
    pass


class BaseRetriever(ABC):
    source: str

    @abstractmethod
    def retrieve(self, project_id: int, query: str, top_k: int) -> list[RetrieverHit]:
        raise NotImplementedError


class BM25Retriever(BaseRetriever):
    source = "bm25"

    def __init__(self, bm25_store: BM25Store | None = None) -> None:
        self.bm25_store = bm25_store or get_bm25_store()

    def retrieve(self, project_id: int, query: str, top_k: int) -> list[RetrieverHit]:
        results = self.bm25_store.search(project_id, query, top_k)
        normalized = normalize_scores({result.chunk_id: result.score for result in results})
        return [
            RetrieverHit(
                chunk_id=result.chunk_id,
                source=self.source,
                raw_score=result.score,
                normalized_score=normalized.get(result.chunk_id, 0.0),
            )
            for result in results
        ]


class VectorRetriever(BaseRetriever):
    source = "vector"

    def __init__(self, vector_store: FaissVectorStore | None = None) -> None:
        self.vector_store = vector_store or get_vector_store()

    def retrieve(self, project_id: int, query: str, top_k: int) -> list[RetrieverHit]:
        results = self.vector_store.search(project_id, query, top_k)
        normalized = normalize_scores({result.chunk_id: result.score for result in results})
        return [
            RetrieverHit(
                chunk_id=result.chunk_id,
                source=self.source,
                raw_score=result.score,
                normalized_score=normalized.get(result.chunk_id, 0.0),
            )
            for result in results
        ]


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, results: list[RetrievalResult], top_k: int) -> list[RetrievalResult]:
        raise NotImplementedError


class NoopReranker(BaseReranker):
    def rerank(self, query: str, results: list[RetrievalResult], top_k: int) -> list[RetrievalResult]:
        return results[:top_k]


class OpenAICompatibleReranker(BaseReranker):
    """LLM-based reranker for OpenAI-compatible chat APIs.

    This is intentionally conservative: if parsing fails, it falls back to the input order.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        self.provider = OpenAICompatibleLLMProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

    def rerank(self, query: str, results: list[RetrievalResult], top_k: int) -> list[RetrievalResult]:
        if not results:
            return []

        candidates = [
            {
                "chunk_id": result.chunk_id,
                "source": result.source,
                "score": result.score,
                "content": result.content[:700],
                "metadata": result.metadata,
            }
            for result in results[: max(top_k * 3, top_k)]
        ]
        messages: list[ChatMessage] = [
            {
                "role": "system",
                "content": (
                    "You are a retrieval reranker. Return only JSON with the shape "
                    '{"chunk_ids":[1,2,3]} ordered by relevance. Do not include explanations.'
                ),
            },
            {
                "role": "user",
                "content": f"Query: {query}\n\nCandidates:\n{json.dumps(candidates, ensure_ascii=False)}",
            },
        ]
        try:
            content = self.provider.generate(messages, temperature=0.0, max_tokens=256)
            ordered_ids = parse_rerank_ids(content)
        except Exception:
            return results[:top_k]

        if not ordered_ids:
            return results[:top_k]

        by_id = {result.chunk_id: result for result in results}
        reranked = [by_id[chunk_id] for chunk_id in ordered_ids if chunk_id in by_id]
        remaining = [result for result in results if result.chunk_id not in set(ordered_ids)]
        return [*reranked, *remaining][:top_k]


def get_reranker() -> BaseReranker:
    settings = get_settings()
    provider = settings.reranker_provider.lower()

    if provider == "noop":
        return NoopReranker()

    if provider in {"openai", "openai_compatible", "qwen", "deepseek"}:
        api_key = settings.reranker_api_key or settings.llm_api_key
        if not api_key:
            raise RuntimeError("RESEARCHFLOW_RERANKER_API_KEY or RESEARCHFLOW_LLM_API_KEY is required for reranker.")
        return OpenAICompatibleReranker(
            api_key=api_key,
            base_url=settings.reranker_base_url or settings.llm_base_url,
            model=settings.reranker_model,
            timeout_seconds=settings.reranker_timeout_seconds,
        )

    raise RuntimeError(f"Unsupported reranker provider: {settings.reranker_provider}")


class HybridRetriever:
    def __init__(
        self,
        vector_store: FaissVectorStore | None = None,
        bm25_store: BM25Store | None = None,
        reranker: BaseReranker | None = None,
    ) -> None:
        self.vector_store = vector_store or get_vector_store()
        self.bm25_store = bm25_store or get_bm25_store()
        self.vector_retriever = VectorRetriever(self.vector_store)
        self.bm25_retriever = BM25Retriever(self.bm25_store)
        self.reranker = reranker or get_reranker()

    def build_project_index(self, db: Session, project_id: int) -> dict[str, int]:
        if db.get(Project, project_id) is None:
            raise ProjectNotFoundForRetrievalError(f"Project not found: {project_id}")

        chunks = self._load_project_chunks(db, project_id)
        chunk_ids = [chunk.id for chunk in chunks]
        texts = [chunk.content for chunk in chunks]

        vector_count = self.vector_store.build(project_id, chunk_ids, texts)
        bm25_count = self.bm25_store.build(project_id, chunk_ids, texts)
        return {"chunk_count": len(chunks), "vector_count": vector_count, "bm25_count": bm25_count}

    def retrieve(
        self,
        db: Session,
        project_id: int,
        query: str,
        top_k: int = 5,
        task_type: str = "general_qa",
    ) -> list[RetrievalResult]:
        if db.get(Project, project_id) is None:
            raise ProjectNotFoundForRetrievalError(f"Project not found: {project_id}")

        search_k = max(top_k * 4, top_k)
        try:
            vector_hits = self.vector_retriever.retrieve(project_id, query, search_k)
            bm25_hits = self.bm25_retriever.retrieve(project_id, query, search_k)
        except (VectorIndexNotFoundError, BM25IndexNotFoundError) as exc:
            raise RetrievalIndexNotFoundError(f"Index not found for project {project_id}; build index first") from exc

        weights = weights_for_task_type(task_type)
        merged = merge_and_deduplicate(
            [*vector_hits, *bm25_hits],
            weights=weights,
            task_type=task_type,
        )
        if not merged:
            return []

        ranked_chunk_ids = [hit.chunk_id for hit in merged]
        chunks_by_id = self._load_chunks_by_id(db, ranked_chunk_ids)
        results: list[RetrievalResult] = []
        for hit in merged:
            chunk = chunks_by_id.get(hit.chunk_id)
            if chunk is None:
                continue
            metadata = parse_metadata(chunk.metadata_json)
            document = chunk.document
            score_breakdown = {
                "final": hit.normalized_score,
                "vector_raw": hit.metadata.get("vector_raw", 0.0),
                "vector_normalized": hit.metadata.get("vector_normalized", 0.0),
                "vector_weight": weights["vector"],
                "bm25_raw": hit.metadata.get("bm25_raw", 0.0),
                "bm25_normalized": hit.metadata.get("bm25_normalized", 0.0),
                "bm25_weight": weights["bm25"],
                "symbol_weight": weights["symbol"],
                "pattern_weight": weights["pattern"],
                "symbol_boost": hit.metadata.get("symbol_boost", 0.0),
                "pattern_boost": hit.metadata.get("pattern_boost", 0.0),
            }
            results.append(
                RetrievalResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    project_id=chunk.project_id,
                    chunk_index=chunk.chunk_index,
                    source=hit.source,
                    content=chunk.content,
                    filename=document.filename,
                    file_type=document.file_type,
                    score=hit.normalized_score,
                    score_breakdown=score_breakdown,
                    metadata=metadata,
                )
            )
        return self.reranker.rerank(query, results, top_k)

    def _load_project_chunks(self, db: Session, project_id: int) -> list[Chunk]:
        statement = select(Chunk).where(Chunk.project_id == project_id).order_by(Chunk.id.asc())
        return list(db.scalars(statement).all())

    def _load_chunks_by_id(self, db: Session, chunk_ids: list[int]) -> dict[int, Chunk]:
        statement = (
            select(Chunk)
            .options(joinedload(Chunk.document))
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.id.in_(chunk_ids))
        )
        chunks = db.scalars(statement).all()
        return {chunk.id: chunk for chunk in chunks}


def merge_and_deduplicate(
    hits: list[RetrieverHit],
    weights: dict[str, float],
    task_type: str,
) -> list[RetrieverHit]:
    by_chunk: dict[int, dict[str, Any]] = {}
    for hit in hits:
        item = by_chunk.setdefault(
            hit.chunk_id,
            {
                "chunk_id": hit.chunk_id,
                "sources": set(),
                "vector_raw": 0.0,
                "vector_normalized": 0.0,
                "bm25_raw": 0.0,
                "bm25_normalized": 0.0,
            },
        )
        item["sources"].add(hit.source)
        if hit.source == "vector":
            item["vector_raw"] = max(item["vector_raw"], hit.raw_score)
            item["vector_normalized"] = max(item["vector_normalized"], hit.normalized_score)
        elif hit.source == "bm25":
            item["bm25_raw"] = max(item["bm25_raw"], hit.raw_score)
            item["bm25_normalized"] = max(item["bm25_normalized"], hit.normalized_score)

    merged: list[RetrieverHit] = []
    for item in by_chunk.values():
        sources = item["sources"]
        symbol_boost = calculate_symbol_boost(task_type, sources, item["bm25_normalized"])
        pattern_boost = calculate_pattern_boost(task_type, sources, item["bm25_normalized"])
        final_score = (
            item["vector_normalized"] * weights["vector"]
            + item["bm25_normalized"] * weights["bm25"]
            + symbol_boost
            + pattern_boost
        )
        source = source_label(sources)
        merged.append(
            RetrieverHit(
                chunk_id=item["chunk_id"],
                source=source,
                raw_score=final_score,
                normalized_score=final_score,
                metadata={
                    "vector_raw": item["vector_raw"],
                    "vector_normalized": item["vector_normalized"],
                    "bm25_raw": item["bm25_raw"],
                    "bm25_normalized": item["bm25_normalized"],
                    "symbol_boost": symbol_boost,
                    "pattern_boost": pattern_boost,
                },
            )
        )
    return sorted(merged, key=lambda hit: hit.normalized_score, reverse=True)


def normalize_scores(scores: dict[int, float]) -> dict[int, float]:
    if not scores:
        return {}
    values = list(scores.values())
    min_score = min(values)
    max_score = max(values)
    if max_score == min_score:
        return {chunk_id: 1.0 for chunk_id in scores}
    return {chunk_id: (score - min_score) / (max_score - min_score) for chunk_id, score in scores.items()}


def weights_for_task_type(task_type: str) -> dict[str, float]:
    if task_type == "paper_qa":
        return {"vector": 0.68, "bm25": 0.28, "symbol": 0.0, "pattern": 0.04}
    if task_type == "repo_qa":
        return {"vector": 0.25, "bm25": 0.50, "symbol": 0.20, "pattern": 0.05}
    if task_type == "log_debug":
        return {"vector": 0.15, "bm25": 0.55, "symbol": 0.0, "pattern": 0.30}
    return {"vector": 0.55, "bm25": 0.45, "symbol": 0.0, "pattern": 0.0}


def calculate_symbol_boost(task_type: str, sources: set[str], bm25_normalized: float) -> float:
    if task_type != "repo_qa" or "bm25" not in sources:
        return 0.0
    return min(bm25_normalized * weights_for_task_type(task_type)["symbol"], 0.20)


def calculate_pattern_boost(task_type: str, sources: set[str], bm25_normalized: float) -> float:
    if task_type not in {"log_debug", "paper_qa"} or "bm25" not in sources:
        return 0.0
    return min(bm25_normalized * weights_for_task_type(task_type)["pattern"], 0.30)


def source_label(sources: set[str]) -> str:
    if sources == {"vector"}:
        return "vector"
    if sources == {"bm25"}:
        return "bm25"
    return "hybrid"


def parse_metadata(metadata_json: str | None) -> dict[str, Any]:
    if not metadata_json:
        return {}
    try:
        value = json.loads(metadata_json)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def parse_rerank_ids(content: str) -> list[int]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return []
        try:
            payload = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return []
    values = payload.get("chunk_ids", []) if isinstance(payload, dict) else []
    return [int(value) for value in values if isinstance(value, int | str) and str(value).isdigit()]
