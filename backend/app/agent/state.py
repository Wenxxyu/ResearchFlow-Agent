from typing import Any, TypedDict


class AgentStep(TypedDict):
    node_name: str
    input: dict[str, Any]
    output: dict[str, Any]
    latency_ms: int


class RetrievedChunk(TypedDict):
    chunk_id: int
    document_id: int
    project_id: int
    chunk_index: int
    content: str
    source: str
    filename: str
    file_type: str
    score: float
    score_breakdown: dict[str, Any]
    vector_score: float
    bm25_score: float
    metadata: dict[str, Any]
    citation: str


class RecalledMemory(TypedDict):
    memory_id: int
    memory_type: str
    content: str
    summary: str | None
    score: float
    importance: float
    confidence: float


class RecalledSkill(TypedDict):
    skill_id: int
    name: str
    description: str | None
    trigger: str | None
    status: str
    score: float
    tools: list[str]
    content_preview: str


class CodeSearchHit(TypedDict):
    path: str
    line_start: int
    line_end: int
    snippet: str
    match_type: str
    symbol_name: str | None
    citation: str


class ParsedLog(TypedDict):
    tail_lines: list[str]
    tail_text: str
    error_type: str | None
    file_references: list[dict[str, Any]]
    keywords: list[str]
    line_count: int


class LogAnalysis(TypedDict):
    summary: str
    possible_causes: list[str]
    troubleshooting_steps: list[str]
    fix_suggestions: list[str]
    need_more_info: list[str]


class AgentState(TypedDict):
    task_id: int
    project_id: int
    conversation_id: str | None
    user_input: str
    task_type: str
    needs_retrieval: bool
    route_reason: str
    route_confidence: float
    route_source: str
    rewritten_query: str
    recalled_skills: list[RecalledSkill]
    recalled_memories: list[RecalledMemory]
    recalled_skill_memories: list[RecalledMemory]
    working_memories: list[RecalledMemory]
    parsed_log: ParsedLog | None
    log_analysis: LogAnalysis | None
    code_search_results: list[CodeSearchHit]
    retrieved_chunks: list[RetrievedChunk]
    selected_evidence: list[RetrievedChunk]
    answer: str
    citations: list[str]
    steps: list[AgentStep]
    errors: list[str]
