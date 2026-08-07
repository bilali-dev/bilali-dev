from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)

UNSUPPORTED_URL = "https://example.com/produto/1"


def _signup(email: str = "customer@example.com") -> dict[str, str]:
    response = client.post("/v1/signup", json={"email": email})
    assert response.status_code == 201
    api_key = response.json()["api_key"]
    return {"Authorization": f"Bearer {api_key}"}


def test_signup_creates_free_plan_customer() -> None:
    response = client.post("/v1/signup", json={"email": "new@example.com"})

    assert response.status_code == 201
    body = response.json()
    assert body["plan"] == "free"
    assert body["api_key"].startswith("sk_live_")


def test_signup_rejects_duplicate_email() -> None:
    client.post("/v1/signup", json={"email": "dup@example.com"})
    response = client.post("/v1/signup", json={"email": "dup@example.com"})

    assert response.status_code == 409


def test_extract_requires_authentication() -> None:
    response = client.post("/v1/extract", json={"url": UNSUPPORTED_URL})

    assert response.status_code == 401


def test_extract_rejects_invalid_api_key() -> None:
    response = client.post(
        "/v1/extract",
        json={"url": UNSUPPORTED_URL},
        headers={"Authorization": "Bearer sk_live_not-a-real-key"},
    )

    assert response.status_code == 401


def test_extract_rejects_unsupported_marketplace() -> None:
    headers = _signup("unsupported@example.com")

    response = client.post("/v1/extract", json={"url": UNSUPPORTED_URL}, headers=headers)

    assert response.status_code == 400


def test_extract_rejects_invalid_body() -> None:
    headers = _signup("invalidbody@example.com")

    response = client.post("/v1/extract", json={"url": "not-a-url"}, headers=headers)

    assert response.status_code == 422


def test_failed_extraction_does_not_consume_quota() -> None:
    headers = _signup("quota@example.com")

    client.post("/v1/extract", json={"url": UNSUPPORTED_URL}, headers=headers)

    usage = client.get("/v1/usage", headers=headers).json()
    assert usage["used_this_month"] == 0
    assert usage["plan"] == "free"
    assert usage["monthly_limit"] == 50


def test_rate_limit_returns_429_after_threshold() -> None:
    original_limit = settings.rate_limit_per_minute
    object.__setattr__(settings, "rate_limit_per_minute", 2)
    try:
        headers = _signup("ratelimited@example.com")

        for _ in range(2):
            response = client.post("/v1/extract", json={"url": UNSUPPORTED_URL}, headers=headers)
            assert response.status_code == 400

        response = client.post("/v1/extract", json={"url": UNSUPPORTED_URL}, headers=headers)
        assert response.status_code == 429
    finally:
        object.__setattr__(settings, "rate_limit_per_minute", original_limit)
