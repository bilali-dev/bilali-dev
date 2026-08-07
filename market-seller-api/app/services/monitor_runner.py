from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.config import settings
from app.db_models import Monitor, MonitorEvent
from app.errors import MarketplaceError
from app.models import ExtractionResult
from app.services.extractor import extract_from_url
from app.services.webhooks import send_webhook

COMPARED_FIELDS: tuple[tuple[str, Callable[[ExtractionResult], object]], ...] = (
    ("product.price", lambda r: r.product.price),
    ("product.availability", lambda r: r.product.availability),
    ("seller.rating", lambda r: r.seller.rating),
    ("seller.reviews_count", lambda r: r.seller.reviews_count),
    ("seller.name", lambda r: r.seller.name),
)


def _dig(data: dict, dotted_key: str) -> object:
    value: object = data
    for part in dotted_key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _diff_events(monitor_id: str, previous: dict | None, current: ExtractionResult) -> list[MonitorEvent]:
    if previous is None:
        return []

    events: list[MonitorEvent] = []
    for field_name, getter in COMPARED_FIELDS:
        previous_value = _dig(previous, field_name)
        current_value = getter(current)
        if previous_value != current_value:
            events.append(
                MonitorEvent(
                    monitor_id=monitor_id,
                    event_type=f"{field_name}_changed",
                    previous_value=str(previous_value) if previous_value is not None else None,
                    current_value=str(current_value) if current_value is not None else None,
                )
            )
    return events


def run_due_monitors(session: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    due_monitors = session.exec(
        select(Monitor).where(Monitor.status == "active", Monitor.next_check_at <= now)
    ).all()

    for monitor in due_monitors:
        _check_monitor(session, monitor, now)
    return len(due_monitors)


def _check_monitor(session: Session, monitor: Monitor, now: datetime) -> None:
    try:
        result = extract_from_url(monitor.url)
    except MarketplaceError:
        monitor.last_checked_at = now
        monitor.next_check_at = now + timedelta(minutes=monitor.frequency_minutes)
        session.add(monitor)
        session.commit()
        return

    events = _diff_events(monitor.id, monitor.last_result, result)
    for event in events:
        session.add(event)

    if events and monitor.webhook_url:
        for event in events:
            send_webhook(
                monitor.webhook_url,
                settings.webhook_secret,
                {
                    "event": event.event_type,
                    "monitor_id": monitor.id,
                    "previous": event.previous_value,
                    "current": event.current_value,
                    "observed_at": now.isoformat(),
                },
            )

    monitor.last_result = result.model_dump(mode="json")
    monitor.last_checked_at = now
    monitor.next_check_at = now + timedelta(minutes=monitor.frequency_minutes)
    session.add(monitor)
    session.commit()
