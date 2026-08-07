from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, select

from app.db import engine
from app.db_models import Customer, Monitor, MonitorEvent, WebhookDelivery
from app.errors import FetchPageError
from app.models import ExtractionResult, ProductData, SellerData
from app.services import monitor_runner
from app.time_utils import utcnow


def _result(price: float) -> ExtractionResult:
    return ExtractionResult(
        marketplace="erli",
        source_url="https://erli.pl/produkt/demo,123",
        product=ProductData(title="Demo", price=price, currency="PLN", availability="Dostępny"),
        seller=SellerData(name="Demo Meble", rating=4.8, reviews_count=725),
    )


def _make_customer(session: Session, email: str = "worker@example.com") -> Customer:
    customer = Customer(email=email)
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


def _make_due_monitor(session: Session, customer: Customer, **overrides) -> Monitor:
    defaults = {
        "customer_id": customer.id,
        "url": "https://erli.pl/produkt/demo,123",
        "frequency_minutes": 60,
        "next_check_at": utcnow() - timedelta(minutes=1),
    }
    defaults.update(overrides)
    monitor = Monitor(**defaults)
    session.add(monitor)
    session.commit()
    session.refresh(monitor)
    return monitor


def test_first_check_stores_baseline_without_events(monkeypatch) -> None:
    monkeypatch.setattr(monitor_runner, "extract_from_url", lambda url: _result(149.9))

    with Session(engine) as session:
        customer = _make_customer(session)
        monitor = _make_due_monitor(session, customer)

        checked = monitor_runner.run_due_monitors(session)

        session.refresh(monitor)
        events = session.exec(
            select(MonitorEvent).where(MonitorEvent.monitor_id == monitor.id)
        ).all()

    assert checked == 1
    assert monitor.last_result["product"]["price"] == 149.9
    assert monitor.last_checked_at is not None
    assert monitor.next_check_at > utcnow()
    assert events == []


def test_price_change_creates_event_and_delivers_webhook(monkeypatch) -> None:
    delivered: list[tuple[str, str, dict]] = []

    def _fake_delivery(url: str, secret: str, event: dict) -> tuple[bool, int, str | None]:
        delivered.append((url, secret, event))
        return True, 1, None

    monkeypatch.setattr(monitor_runner, "send_webhook_with_retry", _fake_delivery)

    results = iter([_result(149.9), _result(139.9)])
    monkeypatch.setattr(monitor_runner, "extract_from_url", lambda url: next(results))

    with Session(engine) as session:
        customer = _make_customer(session)
        monitor = _make_due_monitor(
            session, customer, webhook_url="https://example.com/webhook"
        )

        monitor_runner.run_due_monitors(session)  # baseline check

        monitor.next_check_at = utcnow() - timedelta(minutes=1)
        session.add(monitor)
        session.commit()

        monitor_runner.run_due_monitors(session)  # price changed

        session.refresh(monitor)
        events = session.exec(
            select(MonitorEvent).where(MonitorEvent.monitor_id == monitor.id)
        ).all()
        deliveries = session.exec(
            select(WebhookDelivery).where(WebhookDelivery.monitor_id == monitor.id)
        ).all()
        expected_secret = customer.webhook_secret

    assert len(events) == 1
    assert events[0].event_type == "product.price_changed"
    assert events[0].previous_value == "149.9"
    assert events[0].current_value == "139.9"

    assert len(delivered) == 1
    url, secret, payload = delivered[0]
    assert url == "https://example.com/webhook"
    assert secret == expected_secret
    assert payload["event"] == "product.price_changed"

    assert len(deliveries) == 1
    assert deliveries[0].success is True


def test_failed_webhook_delivery_is_recorded(monkeypatch) -> None:
    monkeypatch.setattr(
        monitor_runner,
        "send_webhook_with_retry",
        lambda url, secret, event: (False, 3, "HTTP 500"),
    )

    results = iter([_result(149.9), _result(139.9)])
    monkeypatch.setattr(monitor_runner, "extract_from_url", lambda url: next(results))

    with Session(engine) as session:
        customer = _make_customer(session)
        monitor = _make_due_monitor(
            session, customer, webhook_url="https://example.com/webhook"
        )

        monitor_runner.run_due_monitors(session)
        monitor.next_check_at = utcnow() - timedelta(minutes=1)
        session.add(monitor)
        session.commit()
        monitor_runner.run_due_monitors(session)

        deliveries = session.exec(
            select(WebhookDelivery).where(WebhookDelivery.monitor_id == monitor.id)
        ).all()

    assert len(deliveries) == 1
    assert deliveries[0].success is False
    assert deliveries[0].attempts == 3
    assert deliveries[0].last_error == "HTTP 500"


def test_extraction_error_reschedules_without_crashing(monkeypatch) -> None:
    def _raise(url: str) -> ExtractionResult:
        raise FetchPageError("boom")

    monkeypatch.setattr(monitor_runner, "extract_from_url", _raise)

    with Session(engine) as session:
        customer = _make_customer(session)
        monitor = _make_due_monitor(session, customer)

        checked = monitor_runner.run_due_monitors(session)

        session.refresh(monitor)

    assert checked == 1
    assert monitor.last_result is None
    assert monitor.last_checked_at is not None
    assert monitor.next_check_at > utcnow()


def test_inactive_monitor_is_skipped(monkeypatch) -> None:
    monkeypatch.setattr(monitor_runner, "extract_from_url", lambda url: _result(149.9))

    with Session(engine) as session:
        customer = _make_customer(session)
        _make_due_monitor(session, customer, status="paused")

        checked = monitor_runner.run_due_monitors(session)

    assert checked == 0


def test_monitor_not_yet_due_is_skipped(monkeypatch) -> None:
    monkeypatch.setattr(monitor_runner, "extract_from_url", lambda url: _result(149.9))

    with Session(engine) as session:
        customer = _make_customer(session)
        _make_due_monitor(
            session, customer, next_check_at=utcnow() + timedelta(hours=1)
        )

        checked = monitor_runner.run_due_monitors(session)

    assert checked == 0


def test_no_webhook_url_means_no_delivery_attempt(monkeypatch) -> None:
    called = False

    def _fake_delivery(*args, **kwargs):
        nonlocal called
        called = True
        return True, 1, None

    monkeypatch.setattr(monitor_runner, "send_webhook_with_retry", _fake_delivery)

    results = iter([_result(149.9), _result(139.9)])
    monkeypatch.setattr(monitor_runner, "extract_from_url", lambda url: next(results))

    with Session(engine) as session:
        customer = _make_customer(session)
        monitor = _make_due_monitor(session, customer)  # no webhook_url

        monitor_runner.run_due_monitors(session)
        monitor.next_check_at = utcnow() - timedelta(minutes=1)
        session.add(monitor)
        session.commit()
        monitor_runner.run_due_monitors(session)

    assert called is False
