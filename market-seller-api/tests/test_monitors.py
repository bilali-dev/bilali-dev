from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.db_models import Customer
from app.main import app

client = TestClient(app)


def _signup(email: str) -> tuple[dict[str, str], str]:
    response = client.post("/v1/signup", json={"email": email})
    assert response.status_code == 201
    body = response.json()
    return {"Authorization": f"Bearer {body['api_key']}"}, body["customer_id"]


def _upgrade_plan(customer_id: str, plan: str) -> None:
    with Session(engine) as session:
        customer = session.exec(select(Customer).where(Customer.id == customer_id)).one()
        customer.plan = plan
        session.add(customer)
        session.commit()


def test_free_plan_cannot_create_monitors() -> None:
    headers, _ = _signup("free-monitor@example.com")

    response = client.post(
        "/v1/monitors",
        json={"url": "https://erli.pl/produkt/demo,123", "frequency_minutes": 1440},
        headers=headers,
    )

    assert response.status_code == 402


def test_starter_plan_can_create_list_get_and_delete_monitor() -> None:
    headers, customer_id = _signup("starter-monitor@example.com")
    _upgrade_plan(customer_id, "starter")

    create_response = client.post(
        "/v1/monitors",
        json={
            "url": "https://erli.pl/produkt/demo,123",
            "frequency_minutes": 1440,
            "webhook_url": "https://example.com/webhook",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    monitor_id = create_response.json()["id"]

    list_response = client.get("/v1/monitors", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/v1/monitors/{monitor_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["url"] == "https://erli.pl/produkt/demo,123"

    delete_response = client.delete(f"/v1/monitors/{monitor_id}", headers=headers)
    assert delete_response.status_code == 204

    missing_response = client.get(f"/v1/monitors/{monitor_id}", headers=headers)
    assert missing_response.status_code == 404


def test_starter_plan_rejects_frequency_below_plan_minimum() -> None:
    headers, customer_id = _signup("frequency@example.com")
    _upgrade_plan(customer_id, "starter")

    response = client.post(
        "/v1/monitors",
        json={"url": "https://erli.pl/produkt/demo,123", "frequency_minutes": 30},
        headers=headers,
    )

    assert response.status_code == 402


def test_monitor_is_not_visible_to_other_customers() -> None:
    headers_a, customer_a = _signup("owner@example.com")
    headers_b, _ = _signup("stranger@example.com")
    _upgrade_plan(customer_a, "starter")

    create_response = client.post(
        "/v1/monitors",
        json={"url": "https://erli.pl/produkt/demo,123", "frequency_minutes": 1440},
        headers=headers_a,
    )
    monitor_id = create_response.json()["id"]

    response = client.get(f"/v1/monitors/{monitor_id}", headers=headers_b)

    assert response.status_code == 404
