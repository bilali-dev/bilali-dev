from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _signup(email: str) -> dict[str, str]:
    response = client.post("/v1/signup", json={"email": email})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['api_key']}"}


def test_checkout_returns_501_when_billing_not_configured() -> None:
    headers = _signup("billing@example.com")

    response = client.post(
        "/v1/billing/checkout",
        json={
            "plan": "starter",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        },
        headers=headers,
    )

    assert response.status_code == 501


def test_webhook_returns_501_when_billing_not_configured() -> None:
    response = client.post("/v1/billing/webhook", content=b"{}")

    assert response.status_code == 501
