import hashlib
import math
import re
from abc import ABC, abstractmethod

import numpy as np

from app.core.config import get_settings


class BaseEmbeddingProvider(ABC):
    dimension: int

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Return a 2D float32 array shaped as (len(texts), dimension)."""

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed_texts([query])[0]


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic hashing embeddings for local development without API keys."""

    def __init__(self, dimension: int = 128) -> None:
        self.dimension = dimension

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for row_index, text in enumerate(texts):
            for token in tokenize_for_embedding(text):
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                bucket = int.from_bytes(digest[:4], "little") % self.dimension
                sign = 1.0 if int.from_bytes(digest[4:], "little") % 2 == 0 else -1.0
                vectors[row_index, bucket] += sign
            norm = float(np.linalg.norm(vectors[row_index]))
            if norm > 0:
                vectors[row_index] /= norm
        return vectors


class OpenAICompatibleEmbeddingProvider(BaseEmbeddingProvider):
    """Embeddings provider for OpenAI-compatible APIs."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        dimension: int = 1536,
        batch_size: int = 10,
        timeout_seconds: float = 60,
    ) -> None:
        from openai import OpenAI

        kwargs = {"api_key": api_key, "timeout": timeout_seconds}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model
        self.dimension = dimension
        self.batch_size = max(1, min(batch_size, 10))

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        all_embeddings: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = self.client.embeddings.create(model=self.model, input=batch)
            all_embeddings.extend(item.embedding for item in response.data)

        vectors = np.array(all_embeddings, dtype=np.float32)
        if vectors.ndim != 2:
            raise RuntimeError("Embedding provider returned invalid vector shape.")
        if vectors.shape[0] != len(texts):
            raise RuntimeError(
                f"Embedding provider returned {vectors.shape[0]} vectors for {len(texts)} input texts."
            )

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vectors = vectors / norms
        self.dimension = int(vectors.shape[1])
        return vectors


def get_embedding_provider() -> BaseEmbeddingProvider:
    settings = get_settings()
    provider = settings.embedding_provider.lower()

    if provider == "mock":
        return MockEmbeddingProvider()

    if provider in {"openai", "openai_compatible", "qwen"}:
        api_key = settings.embedding_api_key or settings.llm_api_key
        if not api_key:
            raise RuntimeError(
                "RESEARCHFLOW_EMBEDDING_API_KEY or RESEARCHFLOW_LLM_API_KEY is required for real embeddings."
            )
        return OpenAICompatibleEmbeddingProvider(
            api_key=api_key,
            base_url=settings.embedding_base_url or settings.llm_base_url,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            batch_size=settings.embedding_batch_size,
            timeout_seconds=settings.embedding_timeout_seconds,
        )

    raise RuntimeError(f"Unsupported embedding provider: {settings.embedding_provider}")


def tokenize_for_embedding(text: str) -> list[str]:
    lowered = text.lower()
    words = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", lowered)
    if not words and lowered:
        words = list(lowered)

    tokens: list[str] = []
    tokens.extend(words)
    tokens.extend(f"{words[index]}{words[index + 1]}" for index in range(len(words) - 1))

    if not tokens and lowered.strip():
        tokens.append(lowered.strip())
    return tokens


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if math.isclose(denominator, 0.0):
        return 0.0
    return float(np.dot(left, right) / denominator)
