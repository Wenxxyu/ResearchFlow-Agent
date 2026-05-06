import ast
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings

IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".idea", ".pytest_cache"}
MAX_FILE_READ_CHARS = 120_000
MAX_API_FILE_CHARS = 40_000
QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "code",
    "does",
    "explain",
    "file",
    "for",
    "function",
    "how",
    "implementation",
    "in",
    "is",
    "of",
    "or",
    "repo",
    "repository",
    "the",
    "to",
    "what",
    "where",
    "which",
}


class RepoError(ValueError):
    pass


@dataclass(frozen=True)
class CodeSearchResult:
    path: str
    line_start: int
    line_end: int
    snippet: str
    match_type: str
    symbol_name: str | None = None


def import_zip_repo(project_id: int, upload_file: UploadFile) -> dict:
    repo_root = project_repo_root(project_id)
    reset_repo_root(repo_root)
    zip_path = repo_root.parent / "repo.zip"
    with zip_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    try:
        safe_extract_zip(zip_path, repo_root)
    finally:
        if zip_path.exists():
            zip_path.unlink()
    return scan_repo(project_id)


def import_local_repo(project_id: int, local_path: str) -> dict:
    source = Path(local_path).resolve()
    workspace = Path.cwd().resolve()
    repo_root = project_repo_root(project_id)
    if not source.exists() or not source.is_dir():
        raise RepoError("Local repository path does not exist or is not a directory")
    if workspace != source and workspace not in source.parents:
        raise RepoError("Local repository path must be inside the current workspace")
    if source == repo_root.resolve() or source in repo_root.resolve().parents:
        raise RepoError("Local repository path cannot contain the managed repository storage directory")

    reset_repo_root(repo_root)
    shutil.copytree(source, repo_root, dirs_exist_ok=True, ignore=ignore_patterns)
    return scan_repo(project_id)


def scan_repo(project_id: int) -> dict:
    repo_root = project_repo_root(project_id)
    if not repo_root.exists():
        raise RepoError("Repository has not been imported for this project")

    files: list[dict] = []
    symbols: list[dict] = []
    tree = build_tree(repo_root)
    readme_summary = ""

    for path in iter_repo_files(repo_root):
        rel_path = to_relative(repo_root, path)
        language = detect_language(path)
        files.append({"path": rel_path, "language": language, "size": path.stat().st_size})
        if path.name.lower().startswith("readme") and not readme_summary:
            readme_summary = read_text_limited(path, 3000)
        if language == "python":
            symbols.extend(extract_python_symbols(repo_root, path))

    index = {
        "project_id": project_id,
        "root": str(repo_root),
        "tree": tree,
        "files": files,
        "symbols": symbols,
        "readme_summary": summarize_readme(readme_summary),
    }
    index_path(project_id).write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def load_repo_index(project_id: int) -> dict:
    path = index_path(project_id)
    if not path.exists():
        return scan_repo(project_id)
    return json.loads(path.read_text(encoding="utf-8"))


def search_repo(project_id: int, query: str, top_k: int = 10) -> list[CodeSearchResult]:
    repo_root = project_repo_root(project_id)
    index = load_repo_index(project_id)
    terms = query_terms(query)
    results: list[CodeSearchResult] = []

    for file_info in index.get("files", []):
        path = file_info["path"]
        if text_matches_terms(Path(path).name.lower(), terms):
            results.append(CodeSearchResult(path=path, line_start=1, line_end=1, snippet=path, match_type="filename"))

    for symbol in index.get("symbols", []):
        if text_matches_terms(symbol["name"].lower(), terms):
            results.append(
                CodeSearchResult(
                    path=symbol["path"],
                    line_start=symbol["line_start"],
                    line_end=symbol["line_end"],
                    snippet=f"{symbol['type']} {symbol['name']}",
                    match_type="symbol",
                    symbol_name=symbol["name"],
                )
            )

    for path in iter_repo_files(repo_root):
        if len(results) >= top_k * 3:
            break
        rel_path = to_relative(repo_root, path)
        text = read_text_limited(path, MAX_FILE_READ_CHARS)
        if not text:
            continue
        lines = text.splitlines()
        for index_line, line in enumerate(lines, start=1):
            if text_matches_terms(line.lower(), terms):
                start = max(index_line - 2, 1)
                end = min(index_line + 2, len(lines))
                snippet = "\n".join(lines[start - 1 : end])
                results.append(
                    CodeSearchResult(
                        path=rel_path,
                        line_start=start,
                        line_end=end,
                        snippet=snippet,
                        match_type="content",
                    )
                )
                break

    return dedupe_results(results)[:top_k]


def query_terms(query: str) -> list[str]:
    terms = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[\u4e00-\u9fff]+", query.lower())
    meaningful = [term for term in terms if len(term) > 1 and term not in QUERY_STOPWORDS]
    return meaningful or [query.lower().strip()]


def text_matches_terms(text: str, terms: list[str]) -> bool:
    return any(term and term in text for term in terms)


def read_repo_file(project_id: int, relative_path: str) -> dict:
    repo_root = project_repo_root(project_id)
    target = safe_repo_path(repo_root, relative_path)
    if not target.exists() or not target.is_file():
        raise RepoError("File not found in repository")
    return {
        "path": to_relative(repo_root, target),
        "content": read_text_limited(target, MAX_API_FILE_CHARS),
        "truncated": target.stat().st_size > MAX_API_FILE_CHARS,
    }


def safe_extract_zip(zip_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            member_path = (target_dir / member.filename).resolve()
            if target_dir.resolve() != member_path and target_dir.resolve() not in member_path.parents:
                raise RepoError("Zip file contains unsafe paths")
        archive.extractall(target_dir)
    flatten_single_root(target_dir)


def flatten_single_root(repo_root: Path) -> None:
    entries = [entry for entry in repo_root.iterdir()]
    if len(entries) != 1 or not entries[0].is_dir():
        return
    nested = entries[0]
    temp = repo_root.parent / "_repo_flatten_tmp"
    if temp.exists():
        shutil.rmtree(temp)
    nested.rename(temp)
    shutil.rmtree(repo_root)
    temp.rename(repo_root)


def build_tree(repo_root: Path) -> list[dict]:
    nodes = []
    for child in sorted(repo_root.iterdir(), key=lambda item: (item.is_file(), item.name.lower())):
        if should_ignore(child):
            continue
        rel_path = to_relative(repo_root, child)
        if child.is_dir():
            nodes.append({"name": child.name, "path": rel_path, "type": "directory", "children": build_tree(child)})
        else:
            nodes.append({"name": child.name, "path": rel_path, "type": "file", "language": detect_language(child)})
    return nodes


def iter_repo_files(repo_root: Path):
    for path in repo_root.rglob("*"):
        if should_ignore(path) or not path.is_file():
            continue
        yield path


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def ignore_patterns(directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_DIRS}


def detect_language(path: Path) -> str:
    suffix_map = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".vue": "vue",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
    }
    return suffix_map.get(path.suffix.lower(), "text")


def extract_python_symbols(repo_root: Path, path: Path) -> list[dict]:
    text = read_text_limited(path, MAX_FILE_READ_CHARS)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    symbols = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(
                {
                    "name": node.name,
                    "type": "class" if isinstance(node, ast.ClassDef) else "function",
                    "path": to_relative(repo_root, path),
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", node.lineno),
                }
            )
    return sorted(symbols, key=lambda item: (item["path"], item["line_start"]))


def read_text_limited(path: Path, limit: int) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def summarize_readme(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())[:1200]


def dedupe_results(results: list[CodeSearchResult]) -> list[CodeSearchResult]:
    seen = set()
    deduped = []
    for result in results:
        key = (result.path, result.line_start, result.match_type, result.symbol_name)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def project_repo_root(project_id: int) -> Path:
    return Path(get_settings().repo_dir) / str(project_id) / "current"


def index_path(project_id: int) -> Path:
    root = project_repo_root(project_id)
    root.parent.mkdir(parents=True, exist_ok=True)
    return root.parent / "repo_index.json"


def reset_repo_root(repo_root: Path) -> None:
    if repo_root.exists():
        shutil.rmtree(repo_root)
    repo_root.mkdir(parents=True, exist_ok=True)


def safe_repo_path(repo_root: Path, relative_path: str) -> Path:
    target = (repo_root / relative_path).resolve()
    root = repo_root.resolve()
    if root != target and root not in target.parents:
        raise RepoError("Path escapes repository root")
    return target


def to_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()
