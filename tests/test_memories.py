from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.memory.manager import MemoryManager


def create_memory_project(client: TestClient) -> int:
    response = client.post("/api/projects", json={"name": "memory-test", "description": "Memory test"})
    assert response.status_code == 201
    return int(response.json()["id"])


def test_create_list_search_and_delete_memory(client: TestClient) -> None:
    project_id = create_memory_project(client)

    create_response = client.post(
        f"/api/projects/{project_id}/memories",
        json={
            "memory_type": "semantic",
            "content": "ResearchFlow-Agent uses hybrid retrieval with BM25 and FAISS.",
            "summary": "Hybrid retrieval uses BM25 and FAISS.",
            "importance": 0.8,
            "confidence": 0.9,
            "tags": ["rag", "retrieval"],
        },
    )

    assert create_response.status_code == 201
    memory = create_response.json()
    assert memory["memory_type"] == "semantic"

    list_response = client.get(f"/api/projects/{project_id}/memories")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    search_response = client.post(
        f"/api/projects/{project_id}/memories/search",
        json={"query": "BM25 FAISS retrieval", "top_k": 3, "memory_type": "semantic"},
    )
    assert search_response.status_code == 200
    results = search_response.json()
    assert len(results) == 1
    assert results[0]["memory"]["id"] == memory["id"]
    assert results[0]["score"] > 0

    delete_response = client.delete(f"/api/memories/{memory['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/projects/{project_id}/memories").json() == []


def test_invalid_memory_type_returns_400(client: TestClient) -> None:
    project_id = create_memory_project(client)

    response = client.post(
        f"/api/projects/{project_id}/memories",
        json={"memory_type": "bad_type", "content": "invalid"},
    )

    assert response.status_code == 400


def test_low_confidence_memory_is_filtered(client: TestClient, db_session: Session) -> None:
    project_id = create_memory_project(client)
    manager = MemoryManager()
    manager.write_memory(
        db=db_session,
        project_id=project_id,
        memory_type="semantic",
        content="Low confidence noisy memory about retrieval.",
        importance=1.0,
        confidence=0.1,
    )

    response = client.post(
        f"/api/projects/{project_id}/memories/search",
        json={"query": "retrieval", "top_k": 5, "min_confidence": 0.4},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_skill_memory_write_and_search(client: TestClient, db_session: Session) -> None:
    project_id = create_memory_project(client)
    manager = MemoryManager()
    memory = manager.write_skill_memory(
        db=db_session,
        project_id=project_id,
        skill_id=7,
        skill_name="pytorch_log_debug",
        task_type="log_debug",
        user_input="RuntimeError: CUDA out of memory",
        outcome="success",
        source_task_id=None,
        answer_preview="Reduce batch size and inspect activation memory.",
    )

    assert memory.memory_type == "skill"
    assert "skill:pytorch_log_debug" in (memory.tags_json or "")

    results = manager.search_skill_memory(
        db=db_session,
        project_id=project_id,
        query="CUDA OOM pytorch debugging",
        top_k=3,
    )

    assert results
    assert results[0].memory.id == memory.id
