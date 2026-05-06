from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True)
class ParsedSection:
    text: str
    page_number: int | None = None


SUPPORTED_DOCUMENT_TYPES = {".pdf", ".md", ".markdown", ".txt"}


class UnsupportedDocumentTypeError(ValueError):
    pass


def parse_document(file_path: Path) -> list[ParsedSection]:
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_TYPES:
        raise UnsupportedDocumentTypeError(f"Unsupported document type: {suffix}")

    if suffix == ".pdf":
        return parse_pdf(file_path)
    return parse_text_file(file_path)


def parse_pdf(file_path: Path) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    with fitz.open(file_path) as document:
        for page_index, page in enumerate(document, start=1):
            text = normalize_text(page.get_text("text"))
            if text:
                sections.append(ParsedSection(text=text, page_number=page_index))
    return sections


def parse_text_file(file_path: Path) -> list[ParsedSection]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    normalized = normalize_text(text)
    return [ParsedSection(text=normalized, page_number=None)] if normalized else []


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    compact_lines: list[str] = []
    blank_seen = False
    for line in lines:
        if not line:
            if not blank_seen:
                compact_lines.append("")
            blank_seen = True
            continue
        compact_lines.append(line)
        blank_seen = False
    return "\n".join(compact_lines).strip()
