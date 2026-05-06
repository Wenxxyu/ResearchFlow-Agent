import pickle
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.core.config import get_settings


@dataclass(frozen=True)
class BM25SearchResult:
    chunk_id: int
    score: float


class BM25IndexNotFoundError(FileNotFoundError):
    pass


class BM25Store:
    def __init__(self, index_root: str = "data/indexes") -> None:
        self.index_root = Path(index_root)

    def build(self, project_id: int, chunk_ids: list[int], texts: list[str]) -> int:
        project_dir = self._project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        tokenized = [tokenize_for_bm25(text) for text in texts]
        payload = {
            "chunk_ids": chunk_ids,
            "tokenized_corpus": tokenized,
            "bm25": BM25Okapi(tokenized) if tokenized else None,
        }
        with self._index_path(project_id).open("wb") as file:
            pickle.dump(payload, file)
        return len(chunk_ids)

    def search(self, project_id: int, query: str, top_k: int) -> list[BM25SearchResult]:
        if top_k <= 0:
            return []

        index_path = self._index_path(project_id)
        if not index_path.exists():
            raise BM25IndexNotFoundError(f"BM25 index not found for project {project_id}")

        with index_path.open("rb") as file:
            payload = pickle.load(file)

        bm25 = payload.get("bm25")
        chunk_ids = [int(chunk_id) for chunk_id in payload.get("chunk_ids", [])]
        if bm25 is None or not chunk_ids:
            return []

        scores = bm25.get_scores(tokenize_for_bm25(query))
        ranked_indexes = sorted(range(len(scores)), key=lambda index: float(scores[index]), reverse=True)

        results: list[BM25SearchResult] = []
        for index in ranked_indexes[:top_k]:
            score = float(scores[index])
            if score <= 0:
                continue
            results.append(BM25SearchResult(chunk_id=chunk_ids[index], score=score))
        return results

    def _project_dir(self, project_id: int) -> Path:
        return self.index_root / str(project_id)

    def _index_path(self, project_id: int) -> Path:
        return self._project_dir(project_id) / "bm25.pkl"


def tokenize_for_bm25(text: str) -> list[str]:
    lowered = text.lower()
    base_tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", lowered)
    tokens: list[str] = []
    tokens.extend(base_tokens)
    tokens.extend(f"{base_tokens[index]}{base_tokens[index + 1]}" for index in range(len(base_tokens) - 1))
    return tokens or [lowered.strip()] if lowered.strip() else []


def get_bm25_store() -> BM25Store:
    return BM25Store(index_root=str(Path(get_settings().upload_dir).parent / "indexes"))
