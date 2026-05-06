from fastapi.testclient import TestClient


def create_project(client: TestClient) -> int:
    response = client.post(
        "/api/projects",
        json={"name": "document-test", "description": "Document upload test"},
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def test_upload_list_get_chunks_and_delete_txt_document(client: TestClient) -> None:
    project_id = create_project(client)
    content = "第一段：ResearchFlow-Agent 支持论文阅读。\n\n第二段：它会解析、切分并写入 chunks 表。"

    upload_response = client.post(
        f"/api/projects/{project_id}/documents/upload",
        files={"file": ("note.txt", content.encode("utf-8"), "text/plain")},
        data={"chunk_size": "24", "chunk_overlap": "4"},
    )

    assert upload_response.status_code == 201
    document = upload_response.json()
    assert document["filename"] == "note.txt"
    assert document["status"] == "indexed"
    assert document["chunk_count"] >= 2

    list_response = client.get(f"/api/projects/{project_id}/documents")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/api/documents/{document['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == document["id"]

    chunks_response = client.get(f"/api/documents/{document['id']}/chunks")
    assert chunks_response.status_code == 200
    chunks = chunks_response.json()
    assert len(chunks) == document["chunk_count"]
    assert chunks[0]["metadata_json"]
    assert "note.txt" in chunks[0]["metadata_json"]

    delete_response = client.delete(f"/api/documents/{document['id']}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/documents/{document['id']}")
    assert missing_response.status_code == 404


def test_upload_rejects_unsupported_file_type(client: TestClient) -> None:
    project_id = create_project(client)

    response = client.post(
        f"/api/projects/{project_id}/documents/upload",
        files={"file": ("data.csv", b"a,b\n1,2", "text/csv")},
    )

    assert response.status_code == 400


def test_list_documents_for_missing_project_returns_404(client: TestClient) -> None:
    response = client.get("/api/projects/999/documents")

    assert response.status_code == 404
