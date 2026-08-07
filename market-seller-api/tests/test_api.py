from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_extract_rejects_unsupported_marketplace() -> None:
    response = client.post("/v1/extract", json={"url": "https://example.com/produto/1"})

    assert response.status_code == 400


def test_extract_rejects_invalid_body() -> None:
    response = client.post("/v1/extract", json={"url": "not-a-url"})

    assert response.status_code == 422
