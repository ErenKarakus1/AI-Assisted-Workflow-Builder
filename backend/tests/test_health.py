from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_not_found_response() -> None:
    client = TestClient(create_app())

    response = client.get("/api/missing-route")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Route not found",
        "path": "/api/missing-route",
    }
