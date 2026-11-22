"""Tests de l'endpoint de santé."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"]
    assert "database" in payload["dependencies"]


def test_root_exposes_docs_and_health() -> None:
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["docs"] == "/docs"
    assert payload["health"] == "/api/v1/health"


def test_unknown_route_uses_standard_error_format() -> None:
    response = client.get("/api/v1/unknown")

    assert response.status_code == 404
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "http_error"
