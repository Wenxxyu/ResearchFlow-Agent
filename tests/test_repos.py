import io
import zipfile

from fastapi.testclient import TestClient


def create_repo_project(client: TestClient) -> int:
    response = client.post("/api/projects", json={"name": "repo-test", "description": "Repo test"})
    assert response.status_code == 201
    return int(response.json()["id"])


def make_repo_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("demo/README.md", "# Demo Repo\n\nA tiny Python repository.")
        archive.writestr(
            "demo/app.py",
            "class Greeter:\n"
            "    def greet(self, name: str) -> str:\n"
            "        return f'Hello {name}'\n\n"
            "def add(left: int, right: int) -> int:\n"
            "    return left + right\n",
        )
        archive.writestr("demo/.git/config", "ignored")
    return buffer.getvalue()


def test_repo_upload_tree_search_and_file_read(client: TestClient) -> None:
    project_id = create_repo_project(client)

    upload_response = client.post(
        f"/api/projects/{project_id}/repos/upload",
        files={"file": ("repo.zip", make_repo_zip(), "application/zip")},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["file_count"] == 2
    assert upload_response.json()["symbol_count"] == 3

    tree_response = client.get(f"/api/projects/{project_id}/repos/tree")
    assert tree_response.status_code == 200
    payload = tree_response.json()
    assert payload["readme_summary"].startswith("# Demo Repo")
    assert any(symbol["name"] == "Greeter" for symbol in payload["symbols"])

    search_response = client.post(
        f"/api/projects/{project_id}/repos/search",
        json={"query": "greet", "top_k": 5},
    )
    assert search_response.status_code == 200
    results = search_response.json()
    assert any(result["match_type"] == "symbol" and result["symbol_name"] == "greet" for result in results)

    file_response = client.get(f"/api/projects/{project_id}/repos/files", params={"path": "app.py"})
    assert file_response.status_code == 200
    assert "class Greeter" in file_response.json()["content"]

    escape_response = client.get(f"/api/projects/{project_id}/repos/files", params={"path": "../README.md"})
    assert escape_response.status_code == 404


def test_agent_repo_qa_uses_code_citations(client: TestClient) -> None:
    project_id = create_repo_project(client)
    assert client.post(
        f"/api/projects/{project_id}/repos/upload",
        files={"file": ("repo.zip", make_repo_zip(), "application/zip")},
    ).status_code == 200

    response = client.post(
        f"/api/projects/{project_id}/agent/chat",
        json={"message": "Explain the greet function in the code"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_type"] == "repo_qa"
    assert "[code:app.py:" in payload["answer"]
    assert "code_search_node" in [step["node_name"] for step in payload["steps"]]
