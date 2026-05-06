from fastapi.testclient import TestClient


def create_skill_project(client: TestClient) -> int:
    response = client.post("/api/projects", json={"name": "skill-test", "description": "Skill test"})
    assert response.status_code == 201
    return int(response.json()["id"])


def test_scan_list_detail_and_search_skills(client: TestClient) -> None:
    project_id = create_skill_project(client)

    scan_response = client.post("/api/skills/scan")
    assert scan_response.status_code == 200
    scan_payload = scan_response.json()
    assert scan_payload["scanned_count"] >= 3

    list_response = client.get("/api/skills")
    assert list_response.status_code == 200
    skills = list_response.json()
    names = {skill["name"] for skill in skills}
    assert {"paper_review", "pytorch_log_debug", "repo_understanding"}.issubset(names)

    paper_skill = next(skill for skill in skills if skill["name"] == "paper_review")
    detail_response = client.get(f"/api/skills/{paper_skill['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert "Paper Review Skill" in detail["content"]
    assert "hybrid_retriever" in detail["tools"]

    search_response = client.post(
        f"/api/projects/{project_id}/skills/search",
        json={"query": "summarize research paper experiments with citations", "top_k": 3},
    )
    assert search_response.status_code == 200
    results = search_response.json()
    assert len(results) > 0
    assert any(result["skill"]["name"] == "paper_review" for result in results)


def test_get_missing_skill_returns_404(client: TestClient) -> None:
    response = client.get("/api/skills/999")

    assert response.status_code == 404
