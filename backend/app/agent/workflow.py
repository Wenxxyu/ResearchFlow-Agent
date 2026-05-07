import json
import time
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.router import IntentRouter
from app.agent.state import AgentState, AgentStep, CodeSearchHit, RecalledMemory, RecalledSkill, RetrievedChunk
from app.llm.provider import BaseLLMProvider, get_llm_provider
from app.memory.manager import MemoryManager
from app.models.task import Task
from app.models.task_step import TaskStep
from app.models.memory import Memory
from app.rag.retriever import RetrievalIndexNotFoundError
from app.repo.manager import RepoError, search_repo
from app.services.retrieval_service import retrieve_project_chunks
from app.skills.registry import SkillRegistry
from app.tools.log_parser import diagnose_from_parsed_log, parse_log_text


def run_agentic_rag_workflow(
    db: Session,
    task_id: int,
    project_id: int,
    user_input: str,
    conversation_id: str | None = None,
    llm_provider: BaseLLMProvider | None = None,
) -> AgentState:
    workflow = AgenticRAGWorkflow(db=db, llm_provider=llm_provider or get_llm_provider())
    initial_state: AgentState = {
        "task_id": task_id,
        "project_id": project_id,
        "conversation_id": conversation_id,
        "user_input": user_input,
        "task_type": "general_chat",
        "needs_retrieval": False,
        "route_reason": "",
        "route_confidence": 0.0,
        "route_source": "init",
        "rewritten_query": "",
        "recalled_skills": [],
        "recalled_memories": [],
        "recalled_skill_memories": [],
        "working_memories": [],
        "parsed_log": None,
        "log_analysis": None,
        "code_search_results": [],
        "retrieved_chunks": [],
        "selected_evidence": [],
        "answer": "",
        "citations": [],
        "steps": [],
        "errors": [],
    }
    return workflow.compile().invoke(initial_state)


class AgenticRAGWorkflow:
    def __init__(self, db: Session, llm_provider: BaseLLMProvider) -> None:
        self.db = db
        self.llm_provider = llm_provider

    def compile(self):
        graph = StateGraph(AgentState)
        graph.add_node("working_memory_recall_node", self._wrap_node("working_memory_recall_node", self.working_memory_recall_node))
        graph.add_node("router_node", self._wrap_node("router_node", self.router_node))
        graph.add_node("direct_answer_node", self._wrap_node("direct_answer_node", self.direct_answer_node))
        graph.add_node("query_rewrite_node", self._wrap_node("query_rewrite_node", self.query_rewrite_node))
        graph.add_node("parse_log_node", self._wrap_node("parse_log_node", self.parse_log_node))
        graph.add_node("memory_recall_node", self._wrap_node("memory_recall_node", self.memory_recall_node))
        graph.add_node("skill_recall_node", self._wrap_node("skill_recall_node", self.skill_recall_node))
        graph.add_node("code_search_node", self._wrap_node("code_search_node", self.code_search_node))
        graph.add_node("retrieval_node", self._wrap_node("retrieval_node", self.retrieval_node))
        graph.add_node("evidence_selection_node", self._wrap_node("evidence_selection_node", self.evidence_selection_node))
        graph.add_node("diagnosis_node", self._wrap_node("diagnosis_node", self.diagnosis_node))
        graph.add_node("fix_suggestion_node", self._wrap_node("fix_suggestion_node", self.fix_suggestion_node))
        graph.add_node("answer_node", self._wrap_node("answer_node", self.answer_node))
        graph.add_node("citation_verify_node", self._wrap_node("citation_verify_node", self.citation_verify_node))
        graph.add_node("working_memory_writer_node", self._wrap_node("working_memory_writer_node", self.working_memory_writer_node))
        graph.add_node("reflection_writer_node", self._wrap_node("reflection_writer_node", self.reflection_writer_node))
        graph.add_node("trace_writer_node", self.trace_writer_node)

        graph.set_entry_point("working_memory_recall_node")
        graph.add_edge("working_memory_recall_node", "router_node")
        graph.add_conditional_edges(
            "router_node",
            route_after_router,
            {
                "direct": "direct_answer_node",
                "log_debug": "parse_log_node",
                "retrieval": "query_rewrite_node",
            },
        )
        graph.add_edge("direct_answer_node", "working_memory_writer_node")
        graph.add_edge("query_rewrite_node", "parse_log_node")
        graph.add_edge("parse_log_node", "memory_recall_node")
        graph.add_edge("memory_recall_node", "skill_recall_node")
        graph.add_edge("skill_recall_node", "code_search_node")
        graph.add_edge("code_search_node", "retrieval_node")
        graph.add_edge("retrieval_node", "evidence_selection_node")
        graph.add_edge("evidence_selection_node", "diagnosis_node")
        graph.add_edge("diagnosis_node", "fix_suggestion_node")
        graph.add_edge("fix_suggestion_node", "answer_node")
        graph.add_edge("answer_node", "citation_verify_node")
        graph.add_edge("citation_verify_node", "working_memory_writer_node")
        graph.add_edge("working_memory_writer_node", "reflection_writer_node")
        graph.add_edge("reflection_writer_node", "trace_writer_node")
        graph.add_edge("trace_writer_node", END)
        return graph.compile()

    def working_memory_recall_node(self, state: AgentState) -> dict[str, Any]:
        if not state["conversation_id"]:
            return {"working_memories": []}

        tag = conversation_tag(state["conversation_id"])
        statement = (
            select(Memory)
            .where(Memory.project_id == state["project_id"], Memory.memory_type == "working")
            .order_by(Memory.created_at.desc())
        )
        memories = []
        for memory in self.db.scalars(statement).all():
            if tag not in load_tags(memory.tags_json):
                continue
            memories.append(memory)
            if len(memories) >= 8:
                break

        recalled: list[RecalledMemory] = []
        for memory in reversed(memories):
            recalled.append(
                {
                    "memory_id": memory.id,
                    "memory_type": memory.memory_type,
                    "content": memory.content,
                    "summary": memory.summary,
                    "score": 1.0,
                    "importance": memory.importance,
                    "confidence": memory.confidence,
                }
            )
        return {"working_memories": recalled}

    def router_node(self, state: AgentState) -> dict[str, Any]:
        intent = IntentRouter(self.llm_provider).classify(state["user_input"])
        return {
            "task_type": intent.task_type,
            "needs_retrieval": intent.needs_retrieval,
            "route_reason": intent.reason,
            "route_confidence": intent.confidence,
            "route_source": intent.source,
        }

    def direct_answer_node(self, state: AgentState) -> dict[str, Any]:
        llm_answer = self.llm_provider.generate(
            [
                {
                    "role": "system",
                    "content": (
                        "You are ResearchFlow-Agent. Answer the user's question directly. "
                        "This route was selected because no external project knowledge is needed. "
                        "Use conversation working memory when it helps resolve references or maintain continuity."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Conversation working memory:\n"
                        + format_working_memory(state)
                        + f"\n\nCurrent question: {state['user_input']}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        return {
            "answer": llm_answer,
            "citations": [],
            "retrieved_chunks": [],
            "selected_evidence": [],
        }

    def query_rewrite_node(self, state: AgentState) -> dict[str, Any]:
        user_input = state["user_input"].strip()
        if state["task_type"] == "paper_qa":
            rewritten = f"{user_input} 方法 实验 结论 evidence"
        elif state["task_type"] == "repo_qa":
            rewritten = f"{user_input} implementation function code"
        elif state["task_type"] == "log_debug":
            rewritten = f"{user_input} error cause fix"
        else:
            rewritten = user_input
        return {"rewritten_query": rewritten}

    def parse_log_node(self, state: AgentState) -> dict[str, Any]:
        if state["task_type"] != "log_debug":
            return {"parsed_log": None}
        parsed = parse_log_text(state["user_input"], tail_lines=80)
        return {"parsed_log": parsed}

    def skill_recall_node(self, state: AgentState) -> dict[str, Any]:
        query = f"{state['task_type']} {state['rewritten_query'] or state['user_input']}"
        if state["task_type"] == "log_debug":
            query = f"pytorch_log_debug CUDA OOM checkpoint NaN shape dtype device traceback {query}"
        results = SkillRegistry().search_skills(
            db=self.db,
            project_id=state["project_id"],
            query=query,
            top_k=3,
            min_score=0.12,
        )
        recalled: list[RecalledSkill] = []
        for result in results:
            skill = result.skill
            recalled.append(
                {
                    "skill_id": skill.id,
                    "name": skill.name,
                    "description": skill.description,
                    "trigger": skill.trigger,
                    "status": skill.status,
                    "score": result.score,
                    "tools": result.tools,
                    "content_preview": result.content_preview,
                }
            )
        SkillRegistry().mark_skills_used(self.db, [skill["skill_id"] for skill in recalled], success=False)
        skill_memory_results = MemoryManager().search_skill_memory(
            db=self.db,
            project_id=state["project_id"],
            query=query,
            top_k=3,
            min_confidence=0.35,
        )
        recalled_skill_memories: list[RecalledMemory] = []
        for result in skill_memory_results:
            memory = result.memory
            recalled_skill_memories.append(
                {
                    "memory_id": memory.id,
                    "memory_type": memory.memory_type,
                    "content": memory.content,
                    "summary": memory.summary,
                    "score": result.score,
                    "importance": memory.importance,
                    "confidence": memory.confidence,
                }
            )
        return {"recalled_skills": recalled, "recalled_skill_memories": recalled_skill_memories}

    def memory_recall_node(self, state: AgentState) -> dict[str, Any]:
        memory_type = memory_type_for_task(state["task_type"])
        results = MemoryManager().search_memory(
            db=self.db,
            project_id=state["project_id"],
            query=state["rewritten_query"] or state["user_input"],
            top_k=5,
            memory_type=memory_type,
            min_confidence=0.4,
        )
        recalled: list[RecalledMemory] = []
        for result in results:
            memory = result.memory
            recalled.append(
                {
                    "memory_id": memory.id,
                    "memory_type": memory.memory_type,
                    "content": memory.content,
                    "summary": memory.summary,
                    "score": result.score,
                    "importance": memory.importance,
                    "confidence": memory.confidence,
                }
            )
        return {"recalled_memories": recalled}

    def code_search_node(self, state: AgentState) -> dict[str, Any]:
        if state["task_type"] != "repo_qa":
            return {"code_search_results": []}
        try:
            results = search_repo(
                project_id=state["project_id"],
                query=state["rewritten_query"] or state["user_input"],
                top_k=5,
            )
        except RepoError as exc:
            return {"code_search_results": [], "errors": [*state["errors"], str(exc)]}

        hits: list[CodeSearchHit] = []
        for result in results:
            citation = f"[code:{result.path}:{result.line_start}]"
            hits.append(
                {
                    "path": result.path,
                    "line_start": result.line_start,
                    "line_end": result.line_end,
                    "snippet": result.snippet,
                    "match_type": result.match_type,
                    "symbol_name": result.symbol_name,
                    "citation": citation,
                }
            )
        return {"code_search_results": hits}

    def retrieval_node(self, state: AgentState) -> dict[str, Any]:
        if state["task_type"] == "log_debug":
            return {"retrieved_chunks": []}
        if not state["needs_retrieval"]:
            return {"retrieved_chunks": []}
        if state["task_type"] == "repo_qa" and state["code_search_results"]:
            return {"retrieved_chunks": []}
        try:
            results = retrieve_project_chunks(
                db=self.db,
                project_id=state["project_id"],
                query=state["rewritten_query"] or state["user_input"],
                top_k=5,
                task_type=state["task_type"],
            )
        except RetrievalIndexNotFoundError as exc:
            return {"retrieved_chunks": [], "errors": [*state["errors"], str(exc)]}

        retrieved_chunks: list[RetrievedChunk] = []
        for result in results:
            citation = f"[doc:{result.filename} chunk:{result.chunk_index}]"
            retrieved_chunks.append(
                {
                    "chunk_id": result.chunk_id,
                    "document_id": result.document_id,
                    "project_id": result.project_id,
                    "chunk_index": result.chunk_index,
                    "content": result.content,
                    "source": result.source,
                    "filename": result.filename,
                    "file_type": result.file_type,
                    "score": result.score,
                    "score_breakdown": result.score_breakdown,
                    "vector_score": result.vector_score,
                    "bm25_score": result.bm25_score,
                    "metadata": result.metadata,
                    "citation": citation,
                }
            )
        return {"retrieved_chunks": retrieved_chunks}

    def evidence_selection_node(self, state: AgentState) -> dict[str, Any]:
        if not state["retrieved_chunks"]:
            return {"selected_evidence": []}
        if state["task_type"] == "general_qa":
            selected = [
                chunk
                for chunk in state["retrieved_chunks"]
                if chunk["score"] >= 0.2 or chunk["score_breakdown"].get("bm25_normalized", 0.0) >= 0.5
            ][:4]
            if not selected and state["needs_retrieval"]:
                selected = state["retrieved_chunks"][:2]
        else:
            selected = state["retrieved_chunks"][:5]
        return {"selected_evidence": selected}

    def diagnosis_node(self, state: AgentState) -> dict[str, Any]:
        if state["task_type"] != "log_debug" or state["parsed_log"] is None:
            return {"log_analysis": state["log_analysis"]}
        analysis = diagnose_from_parsed_log(state["parsed_log"])
        return {"log_analysis": analysis}

    def fix_suggestion_node(self, state: AgentState) -> dict[str, Any]:
        if state["task_type"] != "log_debug" or state["log_analysis"] is None:
            return {"log_analysis": state["log_analysis"]}

        analysis = dict(state["log_analysis"])
        memory_notes = [
            f"Past reflection: {memory['summary'] or memory['content'][:160]}"
            for memory in state["recalled_memories"][:2]
        ]
        skill_notes = [
            f"Skill hint: {skill['name']} - {skill['description'] or skill['trigger'] or ''}"
            for skill in state["recalled_skills"][:2]
        ]
        if memory_notes:
            analysis["troubleshooting_steps"] = [*analysis["troubleshooting_steps"], *memory_notes]
        if skill_notes:
            analysis["fix_suggestions"] = [*analysis["fix_suggestions"], *skill_notes]
        return {"log_analysis": analysis}

    def answer_node(self, state: AgentState) -> dict[str, Any]:
        if state["task_type"] == "log_debug":
            if state["log_analysis"] is None:
                return {
                    "answer": (
                        "I could not extract a recognizable training log or traceback. "
                        "Please paste the full traceback and the last 50-100 training log lines."
                    ),
                    "citations": [],
                }
            answer = format_log_debug_answer(state["log_analysis"])
            return {"answer": answer, "citations": []}

        if state["task_type"] == "general_qa":
            memory_lines = [
                f"[memory:{memory['memory_type']} id:{memory['memory_id']} score:{memory['score']:.3f}] "
                f"{memory['summary'] or memory['content'][:300]}"
                for memory in [*state["recalled_memories"], *state["recalled_skill_memories"]]
            ]
            skill_lines = [
                f"[skill:{skill['name']} score:{skill['score']:.3f}] "
                f"{skill['description'] or ''} Trigger: {skill['trigger'] or ''}"
                for skill in state["recalled_skills"]
            ]
            evidence_lines = [
                f"Source document={chunk['filename']} chunk={chunk['chunk_index']}\n{chunk['content'][:700]}"
                for chunk in state["selected_evidence"]
            ]
            llm_answer = self.llm_provider.generate(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are ResearchFlow-Agent, a research assistant. "
                            "Answer the user's general question directly. "
                            "Use project evidence only when it is clearly relevant to the question. "
                            "If the project evidence is irrelevant, ignore it and answer from general reasoning. "
                            "Do not claim the evidence lacks information when the question is a general fact or calculation. "
                            "Use conversation working memory when it helps resolve references or follow-up questions."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question: {state['user_input']}\n\n"
                            "Conversation working memory:\n"
                            + format_working_memory(state)
                            + "\n\n"
                            "Optional project evidence:\n"
                            + ("\n\n".join(evidence_lines) if evidence_lines else "No retrieved project evidence.")
                            + "\n\n"
                            "Relevant memories:\n"
                            + ("\n".join(memory_lines) if memory_lines else "No recalled memories.")
                            + "\n\n"
                            "Relevant skills:\n"
                            + ("\n".join(skill_lines) if skill_lines else "No recalled skills.")
                        ),
                    },
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            citations = [chunk["citation"] for chunk in state["selected_evidence"]]
            answer = f"{llm_answer}\n\nEvidence used: " + " ".join(citations) if citations else llm_answer
            return {"answer": answer, "citations": citations}

        if not state["selected_evidence"]:
            if state["task_type"] == "repo_qa" and state["code_search_results"]:
                code_lines = []
                citations = []
                for hit in state["code_search_results"]:
                    citations.append(hit["citation"])
                    code_lines.append(f"{hit['citation']}\n{hit['snippet'][:900]}")
                llm_answer = self.llm_provider.generate(
                    [
                        {"role": "system", "content": "Answer using the code snippets. Keep code citations."},
                        {
                        "role": "user",
                        "content": f"Question: {state['user_input']}\n\nCode snippets:\n" + "\n\n".join(code_lines),
                        },
                    ],
                    temperature=0.2,
                    max_tokens=1024,
                )
                return {"answer": f"{llm_answer}\n\nCode references: " + " ".join(citations), "citations": citations}
            if state["errors"]:
                return {
                    "answer": (
                        "I could not retrieve evidence for this project. "
                        "Please upload documents and build the retrieval index first."
                    ),
                    "citations": [],
                }
            return {"answer": "No relevant evidence was found in the current project index.", "citations": []}

        evidence_lines = []
        memory_lines = []
        skill_lines = []
        citations: list[str] = []
        for skill in state["recalled_skills"]:
            skill_lines.append(
                f"[skill:{skill['name']} score:{skill['score']:.3f}] "
                f"{skill['description'] or ''} Trigger: {skill['trigger'] or ''}"
            )
        for memory in [*state["recalled_memories"], *state["recalled_skill_memories"]]:
            memory_lines.append(
                f"[memory:{memory['memory_type']} id:{memory['memory_id']} score:{memory['score']:.3f}] "
                f"{memory['summary'] or memory['content'][:300]}"
            )
        for chunk in state["selected_evidence"]:
            citations.append(chunk["citation"])
            evidence_lines.append(f"{chunk['citation']} {chunk['content'][:700]}")

        llm_answer = self.llm_provider.generate(
            [
                {
                    "role": "system",
                    "content": "Answer using only the provided evidence. Keep citations in the final answer.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {state['user_input']}\n\n"
                        f"Rewritten query: {state['rewritten_query']}\n\n"
                        "Conversation working memory:\n"
                        + format_working_memory(state)
                        + "\n\n"
                        "Relevant memories:\n"
                        + ("\n".join(memory_lines) if memory_lines else "No recalled memories.")
                        + "\n\n"
                        "Relevant skills:\n"
                        + ("\n".join(skill_lines) if skill_lines else "No recalled skills.")
                        + "\n\n"
                        "Evidence:\n" + "\n\n".join(evidence_lines)
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        answer = f"{llm_answer}\n\nEvidence used: " + " ".join(citations)
        return {"answer": answer, "citations": citations}

    def citation_verify_node(self, state: AgentState) -> dict[str, Any]:
        if state["task_type"] in {"general_qa", "log_debug"}:
            return {}
        if not state["citations"]:
            return {"errors": [*state["errors"], "No citations available for the answer."]}

        missing = [citation for citation in state["citations"] if citation not in state["answer"]]
        if not missing:
            return {}

        answer = state["answer"] + "\n\nMissing citation markers appended: " + " ".join(missing)
        return {"answer": answer, "errors": [*state["errors"], f"Missing citations appended: {missing}"]}

    def working_memory_writer_node(self, state: AgentState) -> dict[str, Any]:
        if not state["conversation_id"] or not state["answer"]:
            return {"working_memory_written": False}

        memory = MemoryManager().write_memory(
            db=self.db,
            project_id=state["project_id"],
            memory_type="working",
            content=(
                f"User: {state['user_input']}\n"
                f"Assistant: {state['answer'][:1200]}\n"
                f"Task type: {state['task_type']}\n"
                f"Needs retrieval: {state['needs_retrieval']}"
            ),
            summary=f"Conversation turn for {state['conversation_id']}: {state['user_input'][:120]}",
            importance=0.45,
            confidence=0.85,
            source_task_id=state["task_id"],
            tags=["working", conversation_tag(state["conversation_id"]), state["task_type"]],
        )
        pruned_count = prune_working_memories(
            db=self.db,
            project_id=state["project_id"],
            conversation_id=state["conversation_id"],
            keep_latest=12,
        )
        return {"working_memory_written": True, "working_memory_id": memory.id, "pruned_count": pruned_count}

    def reflection_writer_node(self, state: AgentState) -> dict[str, Any]:
        task = self.db.get(Task, state["task_id"])
        if task is None:
            return {"errors": [*state["errors"], f"Task not found for reflection: {state['task_id']}"]}

        task.task_type = state["task_type"]
        task.final_answer = state["answer"]
        has_evidence = bool(state["retrieved_chunks"] or state["code_search_results"] or state["log_analysis"])
        task.status = "failed" if state["errors"] and not has_evidence else "completed"
        self.db.flush()
        memories = MemoryManager().summarize_task_to_memory(
            db=self.db,
            task=task,
            steps=state["steps"],
            errors=state["errors"],
        )
        if state["task_type"] == "log_debug" and state["log_analysis"] is not None:
            memories.append(
                MemoryManager().write_memory(
                    db=self.db,
                    project_id=state["project_id"],
                    memory_type="reflection",
                    content=(
                        f"Log debug task {task.id}\n"
                        f"Summary: {state['log_analysis']['summary']}\n"
                        f"Likely causes: {'; '.join(state['log_analysis']['possible_causes'])}\n"
                        f"Fix suggestions: {'; '.join(state['log_analysis']['fix_suggestions'])}"
                    ),
                    summary=f"Log debug reflection for task {task.id}: {state['log_analysis']['summary']}",
                    importance=0.72,
                    confidence=0.72,
                    source_task_id=task.id,
                    tags=["reflection", "log_debug"],
                )
            )
        if state["recalled_skills"]:
            success = task.status == "completed" and not state["errors"]
            outcome = "success" if success else "failure"
            for skill in state["recalled_skills"]:
                memories.append(
                    MemoryManager().write_skill_memory(
                        db=self.db,
                        project_id=state["project_id"],
                        skill_id=skill["skill_id"],
                        skill_name=skill["name"],
                        task_type=state["task_type"],
                        user_input=state["user_input"],
                        outcome=outcome,
                        source_task_id=task.id,
                        answer_preview=state["answer"],
                    )
                )
            if success:
                SkillRegistry().mark_skills_succeeded(
                    self.db,
                    [skill["skill_id"] for skill in state["recalled_skills"]],
                )
        return {
            "recalled_memories": state["recalled_memories"],
            "recalled_skill_memories": state["recalled_skill_memories"],
            "reflection_memory_ids": [memory.id for memory in memories],
        }

    def trace_writer_node(self, state: AgentState) -> dict[str, Any]:
        trace_step: AgentStep = {
            "node_name": "trace_writer_node",
            "input": summarize_node_input(state),
            "output": {"stored_step_count": len(state["steps"]) + 1},
            "latency_ms": 0,
        }
        all_steps = [*state["steps"], trace_step]
        for step in all_steps:
            self.db.add(
                TaskStep(
                    task_id=state["task_id"],
                    node_name=step["node_name"],
                    input_json=json.dumps(step["input"], ensure_ascii=False),
                    output_json=json.dumps(step["output"], ensure_ascii=False),
                    latency_ms=step["latency_ms"],
                )
            )
        self.db.commit()
        return {"steps": all_steps}

    def _wrap_node(
        self,
        node_name: str,
        node: Callable[[AgentState], dict[str, Any]],
    ) -> Callable[[AgentState], dict[str, Any]]:
        def wrapped(state: AgentState) -> dict[str, Any]:
            start = time.perf_counter()
            output = node(state)
            latency_ms = int((time.perf_counter() - start) * 1000)
            step: AgentStep = {
                "node_name": node_name,
                "input": summarize_node_input(state),
                "output": make_json_safe(output),
                "latency_ms": latency_ms,
            }
            return {**output, "steps": [*state["steps"], step]}

        return wrapped


def summarize_node_input(state: AgentState) -> dict[str, Any]:
    return {
        "task_id": state["task_id"],
        "project_id": state["project_id"],
        "conversation_id": state["conversation_id"],
        "task_type": state["task_type"],
        "needs_retrieval": state["needs_retrieval"],
        "route_reason": state["route_reason"],
        "route_confidence": state["route_confidence"],
        "route_source": state["route_source"],
        "user_input": state["user_input"],
        "rewritten_query": state["rewritten_query"],
        "retrieved_chunk_count": len(state["retrieved_chunks"]),
        "selected_evidence_count": len(state["selected_evidence"]),
        "code_result_count": len(state["code_search_results"]),
        "recalled_skill_count": len(state["recalled_skills"]),
        "recalled_memory_count": len(state["recalled_memories"]),
        "recalled_skill_memory_count": len(state["recalled_skill_memories"]),
        "working_memory_count": len(state["working_memories"]),
        "log_keyword_count": len(state["parsed_log"]["keywords"]) if state["parsed_log"] else 0,
        "has_log_analysis": bool(state["log_analysis"]),
        "citation_count": len(state["citations"]),
        "error_count": len(state["errors"]),
    }


def make_json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def route_after_router(state: AgentState) -> str:
    if state["task_type"] == "log_debug":
        return "log_debug"
    if state["needs_retrieval"]:
        return "retrieval"
    return "direct"


def conversation_tag(conversation_id: str) -> str:
    return f"conversation:{conversation_id}"


def load_tags(tags_json: str | None) -> list[str]:
    if not tags_json:
        return []
    try:
        value = json.loads(tags_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def format_working_memory(state: AgentState) -> str:
    if not state["working_memories"]:
        return "No prior conversation turns."
    lines = []
    for index, memory in enumerate(state["working_memories"], start=1):
        lines.append(f"Turn {index}: {memory['summary'] or memory['content'][:500]}")
        lines.append(memory["content"][:800])
    return "\n".join(lines)


def prune_working_memories(db: Session, project_id: int, conversation_id: str, keep_latest: int = 12) -> int:
    tag = conversation_tag(conversation_id)
    statement = (
        select(Memory)
        .where(Memory.project_id == project_id, Memory.memory_type == "working")
        .order_by(Memory.created_at.desc())
    )
    matching = [memory for memory in db.scalars(statement).all() if tag in load_tags(memory.tags_json)]
    stale = matching[keep_latest:]
    for memory in stale:
        db.delete(memory)
    if stale:
        db.commit()
    return len(stale)


def memory_type_for_task(task_type: str) -> str | None:
    if task_type == "log_debug":
        return "reflection"
    if task_type == "repo_qa":
        return "skill"
    if task_type == "paper_qa":
        return "semantic"
    return None


def format_log_debug_answer(analysis: dict[str, Any]) -> str:
    sections = [
        ("错误摘要", [analysis["summary"]]),
        ("可能原因", analysis["possible_causes"]),
        ("排查步骤", analysis["troubleshooting_steps"]),
        ("修复建议", analysis["fix_suggestions"]),
        ("需要用户补充的信息", analysis["need_more_info"]),
    ]
    lines = []
    for title, values in sections:
        lines.append(f"## {title}")
        for value in values:
            lines.append(f"- {value}")
        lines.append("")
    lines.append("说明：以上是基于日志模式的规则诊断和 MockLLM 上下文整理；如果日志不完整，不能保证一次性定位根因。")
    return "\n".join(lines).strip()
