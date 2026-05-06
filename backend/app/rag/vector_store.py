import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from app.core.config import get_settings
from app.rag.embeddings import BaseEmbeddingProvider, get_embedding_provider


@dataclass(frozen=True)
class VectorSearchResult:
    chunk_id: int
    score: float


class VectorIndexNotFoundError(FileNotFoundError):
    pass


class FaissVectorStore:
    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider | None = None,
        index_root: str = "data/indexes",
    ) -> None:
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.index_root = Path(index_root)

    def build(self, project_id: int, chunk_ids: list[int], texts: list[str]) -> int:
        project_dir = self._project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        if not texts:
            self._empty_existing_index(project_dir)
            return 0

        vectors = self.embedding_provider.embed_texts(texts).astype(np.float32)
        index = faiss.IndexFlatIP(self.embedding_provider.dimension)
        index.add(vectors)

        faiss.write_index(index, str(self._index_path(project_id)))
        self._mapping_path(project_id).write_text(
            json.dumps({"chunk_ids": chunk_ids}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return len(chunk_ids)

    def search(self, project_id: int, query: str, top_k: int) -> list[VectorSearchResult]:
        if top_k <= 0:
            return []

        index_path = self._index_path(project_id)
        mapping_path = self._mapping_path(project_id)
        if not index_path.exists() or not mapping_path.exists():
            raise VectorIndexNotFoundError(f"Vector index not found for project {project_id}")

        index = faiss.read_index(str(index_path))
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        chunk_ids = [int(chunk_id) for chunk_id in mapping.get("chunk_ids", [])]
        if index.ntotal == 0 or not chunk_ids:
            return []

        query_vector = self.embedding_provider.embed_query(query).astype(np.float32).reshape(1, -1)
        scores, indexes = index.search(query_vector, min(top_k, index.ntotal))

        results: list[VectorSearchResult] = []
        for score, vector_index in zip(scores[0], indexes[0]):
            if vector_index < 0 or vector_index >= len(chunk_ids):
                continue
            results.append(VectorSearchResult(chunk_id=chunk_ids[int(vector_index)], score=float(score)))
        return results

    def _project_dir(self, project_id: int) -> Path:
        return self.index_root / str(project_id)

    def _index_path(self, project_id: int) -> Path:
        return self._project_dir(project_id) / "faiss.index"

    def _mapping_path(self, project_id: int) -> Path:
        return self._project_dir(project_id) / "chunk_mapping.json"

    def _empty_existing_index(self, project_dir: Path) -> None:
        for filename in ("faiss.index", "chunk_mapping.json"):
            path = project_dir / filename
            if path.exists():
                path.unlink()


def get_vector_store() -> FaissVectorStore:
    return FaissVectorStore(index_root=str(Path(get_settings().upload_dir).parent / "indexes"))
