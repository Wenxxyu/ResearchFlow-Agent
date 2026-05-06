from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": "ResearchFlow-Agent",
        "version": "0.1.0",
    }
