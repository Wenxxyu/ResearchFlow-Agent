from fastapi.testclient import TestClient


def prepare_task_for_candidate(client: TestClient) -> tuple[int, int]:
    project_response = client.post(
        "/api/projects",
        json={"name": "candidate-test", "description": "Candidate skill test"},
    )
    assert project_response.status_code == 201
    project_id = int(project_response.json()["id"])

    content = (
        "This paper evaluates experiments and produces citation-grounded answers.\n\n"
        "The workflow uses retrieval, citations, memory, and skill recall."
    )
    upload_response = client.post(
        f"/api/projects/{project_id}/documents/upload",
        files={"file": ("candidate.txt", content.encode("utf-8"), "text/plain")},
        data={"chunk_size": "80", "chunk_overlap": "10"},
    )
    assert upload_response.status_code == 201
    assert client.post(f"/api/projects/{project_id}/index/build").status_code == 200

    chat_response = client.post(
        f"/api/projects/{project_id}/agent/chat",
        json={"message": "Summarize the paper experiments with citations"},
    )
    assert chat_response.status_code == 200
    return project_id, int(chat_response.json()["task_id"])


def test_create_approve_and_register_skill_candidate(client: TestClient) -> None:
    project_id, task_id = prepare_task_for_candidate(client)

    create_response = client.post(
        f"/api/tasks/{task_id}/skill-candidates",
        json={"feedback": "positive"},
    )
    assert create_response.status_code == 201
    candidate = create_response.json()
    assert candidate["status"] == "candidate"
    assert "status: candidate" in candidate["content"]

    list_response = client.get(f"/api/projects/{project_id}/skill-candidates")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    approve_response = client.post(f"/api/skill-candidates/{candidate['id']}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    skills_response = client.get("/api/skills")
    assert skills_response.status_code == 200
    skill_names = {skill["name"] for skill in skills_response.json()}
    assert candidate["name"] in skill_names


def test_reject_skill_candidate(client: TestClient) -> None:
    _, task_id = prepare_task_for_candidate(client)

    create_response = client.post(
        f"/api/tasks/{task_id}/skill-candidates",
        json={"feedback": "positive"},
    )
    assert create_response.status_code == 201
    candidate_id = create_response.json()["id"]

    reject_response = client.post(f"/api/skill-candidates/{candidate_id}/reject")
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"


def test_candidate_for_missing_task_returns_404(client: TestClient) -> None:
    response = client.post("/api/tasks/999/skill-candidates", json={"feedback": "positive"})

    assert response.status_code == 404
