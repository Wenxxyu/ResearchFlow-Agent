from fastapi.testclient import TestClient


def test_create_list_get_and_delete_project(client: TestClient) -> None:
    create_response = client.post(
        "/api/projects",
        json={"name": "demo-project", "description": "A test project"},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] > 0
    assert created["name"] == "demo-project"
    assert created["description"] == "A test project"
    assert "created_at" in created
    assert "updated_at" in created

    list_response = client.get("/api/projects")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/api/projects/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "demo-project"

    delete_response = client.delete(f"/api/projects/{created['id']}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/projects/{created['id']}")
    assert missing_response.status_code == 404


def test_create_project_conflict(client: TestClient) -> None:
    payload = {"name": "duplicate", "description": None}

    assert client.post("/api/projects", json=payload).status_code == 201
    response = client.post("/api/projects", json=payload)

    assert response.status_code == 409


def test_delete_missing_project_returns_404(client: TestClient) -> None:
    response = client.delete("/api/projects/999")

    assert response.status_code == 404
