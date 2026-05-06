from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.task_step import TaskStep
from app.models.memory import Memory


def prepare_project_for_agent(client: TestClient) -> int:
    project_response = client.post(
        "/api/projects",
        json={"name": "agent-test", "description": "Agentic RAG test"},
    )
    assert project_response.status_code == 201
    project_id = int(project_response.json()["id"])

    content = (
        "ResearchFlow-Agent supports Agentic RAG for paper reading.\n\n"
        "It combines BM25 keyword retrieval, FAISS vector retrieval, and traceable citations.\n\n"
        "Every final answer should include citation markers."
    )
    upload_response = client.post(
        f"/api/projects/{project_id}/documents/upload",
        files={"file": ("agent.txt", content.encode("utf-8"), "text/plain")},
        data={"chunk_size": "90", "chunk_overlap": "10"},
    )
    assert upload_response.status_code == 201

    build_response = client.post(f"/api/projects/{project_id}/index/build")
    assert build_response.status_code == 200
    return project_id


def test_agent_chat_writes_task_steps_and_citations(client: TestClient, db_session: Session) -> None:
    project_id = prepare_project_for_agent(client)

    response = client.post(
        f"/api/projects/{project_id}/agent/chat",
        json={"message": "What retrieval methods does this project use?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] > 0
    assert payload["task_type"] in {"paper_qa", "general_qa"}
    assert "[doc:agent.txt chunk:" in payload["answer"]
    assert len(payload["citations"]) > 0
    assert "router_node" in [step["node_name"] for step in payload["steps"]]
    assert "skill_recall_node" in [step["node_name"] for step in payload["steps"]]
    assert "trace_writer_node" in [step["node_name"] for step in payload["steps"]]

    statement = select(TaskStep).where(TaskStep.task_id == payload["task_id"])
    stored_steps = db_session.scalars(statement).all()
    assert len(stored_steps) == len(payload["steps"])
    assert stored_steps[0].node_name == "working_memory_recall_node"

    memories = db_session.query(Memory).filter(Memory.source_task_id == payload["task_id"]).all()
    assert any(memory.memory_type == "episodic" for memory in memories)


def test_agent_chat_uses_conversation_working_memory(client: TestClient, db_session: Session) -> None:
    project_response = client.post(
        "/api/projects",
        json={"name": "working-memory-test", "description": "Working memory test"},
    )
    assert project_response.status_code == 201
    project_id = int(project_response.json()["id"])
    conversation_id = "test-conv-working-memory"

    first_response = client.post(
        f"/api/projects/{project_id}/agent/chat",
        json={"message": "My favorite framework is LangGraph.", "conversation_id": conversation_id},
    )
    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["conversation_id"] == conversation_id
    first_step_names = [step["node_name"] for step in first_payload["steps"]]
    assert "working_memory_recall_node" in first_step_names
    assert "working_memory_writer_node" in first_step_names

    working_memories = (
        db_session.query(Memory)
        .filter(Memory.project_id == project_id, Memory.memory_type == "working")
        .all()
    )
    assert any(f"conversation:{conversation_id}" in (memory.tags_json or "") for memory in working_memories)

    second_response = client.post(
        f"/api/projects/{project_id}/agent/chat",
        json={"message": "What framework did I say I liked?", "conversation_id": conversation_id},
    )
    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["conversation_id"] == conversation_id
    recall_steps = [
        step for step in second_payload["steps"] if step["node_name"] == "working_memory_recall_node"
    ]
    assert recall_steps
    assert recall_steps[0]["output"]["working_memories"]


def test_agent_chat_missing_project_returns_404(client: TestClient) -> None:
    response = client.post("/api/projects/999/agent/chat", json={"message": "hello"})

    assert response.status_code == 404


def test_agent_general_chat_falls_back_to_llm_without_evidence(client: TestClient) -> None:
    project_response = client.post(
        "/api/projects",
        json={"name": "general-chat-test", "description": "General chat test"},
    )
    assert project_response.status_code == 201
    project_id = int(project_response.json()["id"])

    response = client.post(
        f"/api/projects/{project_id}/agent/chat",
        json={"message": "Who are you?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_type"] == "general_qa"
    assert "No relevant evidence was found" not in payload["answer"]
    assert payload["answer"]
    assert payload["citations"] == []
    assert not any("No citations available" in error for error in payload["errors"])


def test_agent_general_chat_does_not_use_irrelevant_document_evidence(client: TestClient) -> None:
    project_id = prepare_project_for_agent(client)

    response = client.post(
        f"/api/projects/{project_id}/agent/chat",
        json={"message": "What is 1+1?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_type"] == "general_qa"
    assert payload["answer"]
    assert "No relevant evidence was found" not in payload["answer"]
    assert "direct_answer_node" in [step["node_name"] for step in payload["steps"]]
    assert "retrieval_node" not in [step["node_name"] for step in payload["steps"]]
    assert payload["citations"] == []


def test_agent_log_debug_returns_structured_analysis(client: TestClient, db_session: Session) -> None:
    project_response = client.post(
        "/api/projects",
        json={"name": "log-debug-test", "description": "Log debug test"},
    )
    assert project_response.status_code == 201
    project_id = int(project_response.json()["id"])

    log_text = (
        "Epoch 1 step 42 loss=1.23\n"
        "Traceback (most recent call last):\n"
        "  File \"train.py\", line 88, in train_one_epoch\n"
        "    loss.backward()\n"
        "RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB\n"
    )

    response = client.post(
        f"/api/projects/{project_id}/agent/chat",
        json={"message": log_text},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_type"] == "log_debug"
    assert payload["log_analysis"]["summary"]
    assert "OOM" in [step["output"].get("parsed_log", {}).get("keywords", []) for step in payload["steps"] if step["node_name"] == "parse_log_node"][0]
    assert "错误摘要" in payload["answer"]
    assert "修复建议" in payload["answer"]
    assert "parse_log_node" in [step["node_name"] for step in payload["steps"]]
    assert "diagnosis_node" in [step["node_name"] for step in payload["steps"]]
    assert "fix_suggestion_node" in [step["node_name"] for step in payload["steps"]]

    memories = db_session.query(Memory).filter(Memory.source_task_id == payload["task_id"]).all()
    assert any(memory.memory_type == "reflection" and "Log debug task" in memory.content for memory in memories)


def test_agent_writes_skill_memory_for_recalled_skill(client: TestClient, db_session: Session) -> None:
    project_response = client.post(
        "/api/projects",
        json={"name": "agent-skill-memory-test", "description": "Agent skill memory test"},
    )
    assert project_response.status_code == 201
    project_id = int(project_response.json()["id"])

    scan_response = client.post("/api/skills/scan")
    assert scan_response.status_code == 200

    log_text = (
        "Traceback (most recent call last):\n"
        "  File \"train.py\", line 12, in <module>\n"
        "    output = model(batch)\n"
        "RuntimeError: CUDA out of memory. Tried to allocate 1.00 GiB\n"
    )
    response = client.post(
        f"/api/projects/{project_id}/agent/chat",
        json={"message": log_text},
    )

    assert response.status_code == 200
    payload = response.json()
    skill_steps = [step for step in payload["steps"] if step["node_name"] == "skill_recall_node"]
    assert skill_steps
    assert skill_steps[0]["output"]["recalled_skills"]

    skill_memories = (
        db_session.query(Memory)
        .filter(Memory.project_id == project_id, Memory.memory_type == "skill")
        .all()
    )
    assert skill_memories
    assert any("pytorch_log_debug" in memory.content for memory in skill_memories)
