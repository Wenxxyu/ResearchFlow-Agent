from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    content: str
    start_index: int
    end_index: int


class RecursiveTextSplitter:
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        separators: list[str] | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be greater than or equal to 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", "；", "，", " ", ""]

    def split_text(self, text: str) -> list[TextChunk]:
        text = text.strip()
        if not text:
            return []

        raw_chunks = self._split_recursive(text, self.separators)
        merged = self._merge_chunks(raw_chunks)
        return self._with_offsets(text, merged)

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        separator = separators[0]
        rest = separators[1:]
        if separator == "":
            return [text[index : index + self.chunk_size] for index in range(0, len(text), self.chunk_size)]

        pieces = text.split(separator)
        if len(pieces) == 1:
            return self._split_recursive(text, rest)

        chunks: list[str] = []
        for index, piece in enumerate(pieces):
            if not piece:
                continue
            candidate = piece if index == len(pieces) - 1 else piece + separator
            if len(candidate) <= self.chunk_size:
                chunks.append(candidate)
            else:
                chunks.extend(self._split_recursive(candidate, rest))
        return chunks

    def _merge_chunks(self, chunks: list[str]) -> list[str]:
        merged: list[str] = []
        current = ""

        for chunk in chunks:
            if not current:
                current = chunk
                continue

            if len(current) + len(chunk) <= self.chunk_size:
                current += chunk
                continue

            merged.append(current.strip())
            overlap = current[-self.chunk_overlap :] if self.chunk_overlap else ""
            current = overlap + chunk

            while len(current) > self.chunk_size:
                merged.append(current[: self.chunk_size].strip())
                overlap = current[self.chunk_size - self.chunk_overlap : self.chunk_size] if self.chunk_overlap else ""
                current = overlap + current[self.chunk_size :]

        if current.strip():
            merged.append(current.strip())
        return [chunk for chunk in merged if chunk]

    def _with_offsets(self, text: str, chunks: list[str]) -> list[TextChunk]:
        result: list[TextChunk] = []
        search_from = 0
        for chunk in chunks:
            start = text.find(chunk, search_from)
            if start < 0:
                start = max(0, search_from - self.chunk_overlap)
            end = start + len(chunk)
            result.append(TextChunk(content=chunk, start_index=start, end_index=end))
            search_from = max(start + 1, end - self.chunk_overlap)
        return result
