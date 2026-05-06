from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ParsedSkill:
    name: str
    description: str
    tools: list[str] = field(default_factory=list)
    status: str = "draft"
    trigger: str = ""
    path: str = ""
    content: str = ""
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)


class SkillParseError(ValueError):
    pass


def parse_skill_file(skill_file: Path) -> ParsedSkill:
    if not skill_file.exists():
        raise SkillParseError(f"SKILL.md not found: {skill_file}")

    raw = skill_file.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(raw)

    name = str(frontmatter.get("name") or skill_file.parent.name).strip()
    description = str(frontmatter.get("description") or "").strip()
    status = str(frontmatter.get("status") or "draft").strip()
    trigger = str(frontmatter.get("trigger") or description).strip()
    tools = parse_tools(frontmatter.get("tools"))

    if not name:
        raise SkillParseError(f"Skill name is empty: {skill_file}")

    return ParsedSkill(
        name=name,
        description=description,
        tools=tools,
        status=status,
        trigger=trigger,
        path=str(skill_file.parent),
        content=body.strip(),
        raw_frontmatter=frontmatter,
    )


def split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        return {}, normalized

    parts = normalized.split("\n---\n", 1)
    if len(parts) != 2:
        raise SkillParseError("Invalid YAML frontmatter boundary")

    frontmatter_text = parts[0].replace("---\n", "", 1)
    body = parts[1]
    loaded = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(loaded, dict):
        raise SkillParseError("YAML frontmatter must be a mapping")
    return loaded, body


def parse_tools(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []
