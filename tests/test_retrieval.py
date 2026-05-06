from fastapi.testclient import TestClient


def create_project_with_document(client: TestClient) -> tuple[int, int]:
    project_response = client.post(
        "/api/projects",
        json={"name": "retrieval-test", "description": "Retrieval test"},
    )
    assert project_response.status_code == 201
    project_id = int(project_response.json()["id"])

    content = (
        "Graph neural networks are useful for citation networks.\n\n"
        "ResearchFlow-Agent uses hybrid retrieval with BM25 and vector search.\n\n"
        "中文检索也应该能够处理论文、实验日志和代码仓库内容。"
    )
    upload_response = client.post(
        f"/api/projects/{project_id}/documents/upload",
        files={"file": ("retrieval.txt", content.encode("utf-8"), "text/plain")},
        data={"chunk_size": "48", "chunk_overlap": "8"},
    )
    assert upload_response.status_code == 201
    return project_id, int(upload_response.json()["id"])


def test_build_index_and_retrieve(client: TestClient) -> None:
    project_id, _ = create_project_with_document(client)

    build_response = client.post(f"/api/projects/{project_id}/index/build")
    assert build_response.status_code == 200
    build_payload = build_response.json()
    assert build_payload["status"] == "built"
    assert build_payload["chunk_count"] > 0
    assert build_payload["vector_count"] == build_payload["chunk_count"]
    assert build_payload["bm25_count"] == build_payload["chunk_count"]

    retrieve_response = client.post(
        f"/api/projects/{project_id}/retrieve",
        json={"query": "hybrid retrieval BM25 vector search", "top_k": 3},
    )
    assert retrieve_response.status_code == 200
    payload = retrieve_response.json()
    assert payload["query"] == "hybrid retrieval BM25 vector search"
    assert len(payload["results"]) > 0
    assert "hybrid retrieval" in payload["results"][0]["content"].lower()
    assert payload["results"][0]["filename"] == "retrieval.txt"
    assert payload["results"][0]["source"] in {"bm25", "vector", "hybrid"}
    assert "score_breakdown" in payload["results"][0]
    assert "vector_normalized" in payload["results"][0]["score_breakdown"]
    assert "bm25_normalized" in payload["results"][0]["score_breakdown"]
    assert "chunk_index" in payload["results"][0]["metadata"]


def test_retrieve_before_build_returns_409(client: TestClient) -> None:
    project_id, _ = create_project_with_document(client)

    response = client.post(
        f"/api/projects/{project_id}/retrieve",
        json={"query": "retrieval", "top_k": 3},
    )

    assert response.status_code == 409


def test_build_index_missing_project_returns_404(client: TestClient) -> None:
    response = client.post("/api/projects/999/index/build")

    assert response.status_code == 404
