import json
import re
from dataclasses import dataclass
from typing import Literal

from app.llm.provider import BaseLLMProvider

TaskType = Literal["general_qa", "paper_qa", "repo_qa", "log_debug"]

VALID_TASK_TYPES: set[str] = {"general_qa", "paper_qa", "repo_qa", "log_debug"}

LOG_DEBUG_KEYWORDS = [
    "traceback",
    "cuda out of memory",
    "runtimeerror",
    "shape mismatch",
    "size mismatch",
    "nan loss",
    "loss nan",
    "checkpoint loading failed",
    "module not found",
    "modulenotfounderror",
    "permissionerror",
    "oom",
    "日志",
    "报错",
    "错误",
    "异常",
]

PAPER_QA_KEYWORDS = [
    "论文",
    "文档",
    "上传",
    "pdf",
    "paper",
    "citation",
    "method",
    "experiment",
    "实验",
    "方法",
    "结论",
    "根据文档",
    "根据论文",
]

REPO_QA_KEYWORDS = [
    "代码",
    "仓库",
    "函数",
    "类",
    "文件",
    "实现",
    "repo",
    "repository",
    "function",
    "class",
    "module",
    "import",
]

DIRECT_ANSWER_PATTERNS = [
    "1+1",
    "1 + 1",
    "你是谁",
    "who are you",
    "hello",
    "hi",
    "你好",
]

PROJECT_RETRIEVAL_KEYWORDS = [
    "根据",
    "上传",
    "文档",
    "论文",
    "pdf",
    "项目",
    "资料",
    "知识库",
    "总结",
    "介绍",
    "是什么",
    "有哪些",
    "技术栈",
    "retrieval",
    "method",
    "methods",
    "this project",
    "uses",
]


@dataclass(frozen=True)
class IntentResult:
    task_type: TaskType
    needs_retrieval: bool
    confidence: float
    reason: str
    source: Literal["rule", "llm", "fallback"]


class IntentRouter:
    def __init__(self, llm_provider: BaseLLMProvider, llm_confidence_threshold: float = 0.55) -> None:
        self.llm_provider = llm_provider
        self.llm_confidence_threshold = llm_confidence_threshold

    def classify(self, user_input: str) -> IntentResult:
        stripped = user_input.strip()

        strong_rule = classify_by_strong_rule(stripped)
        if strong_rule is not None:
            return strong_rule

        llm_result = self._classify_with_llm(stripped)
        if llm_result is not None and llm_result.confidence >= self.llm_confidence_threshold:
            return llm_result

        fallback = classify_by_fallback_rule(stripped)
        if llm_result is None:
            return fallback

        return IntentResult(
            task_type=fallback.task_type,
            needs_retrieval=fallback.needs_retrieval,
            confidence=min(fallback.confidence, llm_result.confidence),
            reason=(
                f"LLM intent confidence too low or unsafe; using fallback. "
                f"LLM said {llm_result.task_type} confidence={llm_result.confidence:.2f}. "
                f"Fallback reason: {fallback.reason}"
            ),
            source="fallback",
        )

    def _classify_with_llm(self, user_input: str) -> IntentResult | None:
        try:
            raw = self.llm_provider.generate(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are the intent classifier for ResearchFlow-Agent. "
                            "Return only valid JSON. Do not add markdown."
                        ),
                    },
                    {"role": "user", "content": render_intent_prompt(user_input)},
                ],
                temperature=0.0,
                max_tokens=256,
            )
            payload = extract_json_object(raw)
            task_type = str(payload.get("task_type", "")).strip()
            if task_type not in VALID_TASK_TYPES:
                return None
            confidence = clamp_float(payload.get("confidence", 0.0))
            needs_retrieval = bool(payload.get("needs_retrieval", False))
            if task_type in {"paper_qa", "repo_qa"}:
                needs_retrieval = True
            if task_type == "log_debug":
                needs_retrieval = False
            return IntentResult(
                task_type=task_type,  # type: ignore[arg-type]
                needs_retrieval=needs_retrieval,
                confidence=confidence,
                reason=str(payload.get("reason") or "Classified by LLM intent classifier.")[:500],
                source="llm",
            )
        except Exception:
            return None


def classify_by_strong_rule(user_input: str) -> IntentResult | None:
    lowered = user_input.lower()
    matched_log = matched_keywords(lowered, LOG_DEBUG_KEYWORDS)
    if matched_log:
        return IntentResult(
            task_type="log_debug",
            needs_retrieval=False,
            confidence=0.96,
            reason=f"Strong log/debug pattern matched: {', '.join(matched_log[:4])}.",
            source="rule",
        )

    matched_direct = matched_keywords(lowered, DIRECT_ANSWER_PATTERNS)
    if matched_direct:
        return IntentResult(
            task_type="general_qa",
            needs_retrieval=False,
            confidence=0.95,
            reason=f"Direct-answer pattern matched: {', '.join(matched_direct[:3])}.",
            source="rule",
        )

    matched_paper = matched_keywords(lowered, PAPER_QA_KEYWORDS)
    matched_repo = matched_keywords(lowered, REPO_QA_KEYWORDS)
    if matched_paper and len(matched_paper) >= len(matched_repo):
        return IntentResult(
            task_type="paper_qa",
            needs_retrieval=True,
            confidence=0.86,
            reason=f"Strong paper/document pattern matched: {', '.join(matched_paper[:4])}.",
            source="rule",
        )

    if matched_repo:
        return IntentResult(
            task_type="repo_qa",
            needs_retrieval=True,
            confidence=0.86,
            reason=f"Strong repository/code pattern matched: {', '.join(matched_repo[:4])}.",
            source="rule",
        )

    matched_project = matched_keywords(lowered, PROJECT_RETRIEVAL_KEYWORDS)
    if matched_project:
        return IntentResult(
            task_type="general_qa",
            needs_retrieval=True,
            confidence=0.84,
            reason=f"Strong project-knowledge pattern matched: {', '.join(matched_project[:4])}.",
            source="rule",
        )

    return None


def classify_by_fallback_rule(user_input: str) -> IntentResult:
    lowered = user_input.lower()
    matched_paper = matched_keywords(lowered, PAPER_QA_KEYWORDS)
    matched_repo = matched_keywords(lowered, REPO_QA_KEYWORDS)

    if matched_paper and len(matched_paper) >= len(matched_repo):
        return IntentResult(
            task_type="paper_qa",
            needs_retrieval=True,
            confidence=0.72,
            reason=f"Fallback paper/document keywords matched: {', '.join(matched_paper[:4])}.",
            source="fallback",
        )

    if matched_repo:
        return IntentResult(
            task_type="repo_qa",
            needs_retrieval=True,
            confidence=0.72,
            reason=f"Fallback repository/code keywords matched: {', '.join(matched_repo[:4])}.",
            source="fallback",
        )

    needs_retrieval = infer_general_retrieval_need(user_input)
    return IntentResult(
        task_type="general_qa",
        needs_retrieval=needs_retrieval,
        confidence=0.62 if needs_retrieval else 0.68,
        reason=(
            "Fallback general query appears to ask about project-specific knowledge."
            if needs_retrieval
            else "Fallback general query does not need external project knowledge."
        ),
        source="fallback",
    )


def infer_general_retrieval_need(user_input: str) -> bool:
    lowered = user_input.strip().lower()
    if matched_keywords(lowered, DIRECT_ANSWER_PATTERNS):
        return False
    return bool(matched_keywords(lowered, PROJECT_RETRIEVAL_KEYWORDS))


def matched_keywords(lowered_text: str, keywords: list[str]) -> list[str]:
    matches = []
    for keyword in keywords:
        lowered_keyword = keyword.lower()
        if is_plain_word(lowered_keyword):
            if re.search(rf"\b{re.escape(lowered_keyword)}\b", lowered_text):
                matches.append(keyword)
            continue
        if lowered_keyword in lowered_text:
            matches.append(keyword)
    return matches


def is_plain_word(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_]+", value))


def render_intent_prompt(user_input: str) -> str:
    return f"""Classify the user query for ResearchFlow-Agent.

Task types:
- general_qa: General question or conversation. Use retrieval only if it asks about uploaded/project-specific knowledge.
- paper_qa: Question about uploaded papers/documents, paper methods, experiments, citations, summaries.
- repo_qa: Question about code repositories, files, functions, classes, implementation, code errors.
- log_debug: Training logs, tracebacks, runtime errors, CUDA OOM, shape mismatch, NaN loss, checkpoint errors.

Return JSON only:
{{
  "task_type": "general_qa | paper_qa | repo_qa | log_debug",
  "needs_retrieval": true,
  "confidence": 0.0,
  "reason": "short reason"
}}

User query:
{user_input}
"""


def extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM router output")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("LLM router output is not a JSON object")
    return value


def clamp_float(value: object, lower: float = 0.0, upper: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return min(max(number, lower), upper)
