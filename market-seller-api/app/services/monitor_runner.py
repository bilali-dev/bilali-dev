from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.config import settings
from app.db_models import Customer, Monitor, MonitorEvent, WebhookDelivery
from app.errors import MarketplaceError
from app.models import ExtractionResult
from app.services.extractor import extract_from_url
from app.services.webhooks import send_webhook_with_retry
from app.time_utils import utcnow

logger = logging.getLogger(__name__)

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
    now = now or utcnow()
    due_monitors = session.exec(
        select(Monitor).where(Monitor.status == "active", Monitor.next_check_at <= now)
    ).all()

    for monitor in due_monitors:
        _check_monitor(session, monitor, now)
    return len(due_monitors)


def _webhook_secret_for(session: Session, customer_id: str) -> str:
    customer = session.get(Customer, customer_id)
    if customer is None:
        logger.warning("Monitor references unknown customer %s; using fallback webhook secret.", customer_id)
        return settings.webhook_secret
    return customer.webhook_secret


def _deliver_events(session: Session, monitor: Monitor, events: list[MonitorEvent], now: datetime) -> None:
    if not events or not monitor.webhook_url:
        return

    secret = _webhook_secret_for(session, monitor.customer_id)
    for event in events:
        success, attempts, error = send_webhook_with_retry(
            monitor.webhook_url,
            secret,
            {
                "event": event.event_type,
                "monitor_id": monitor.id,
                "previous": event.previous_value,
                "current": event.current_value,
                "observed_at": now.isoformat(),
            },
        )
        session.add(
            WebhookDelivery(
                monitor_id=monitor.id,
                event_type=event.event_type,
                url=monitor.webhook_url,
                success=success,
                attempts=attempts,
                last_error=error,
            )
        )
        if not success:
            logger.warning(
                "Webhook delivery failed for monitor %s (%s) after %s attempt(s): %s",
                monitor.id,
                event.event_type,
                attempts,
                error,
            )


def _check_monitor(session: Session, monitor: Monitor, now: datetime) -> None:
    try:
        result = extract_from_url(monitor.url)
    except MarketplaceError as exc:
        logger.warning("Monitor %s failed to extract %s: %s", monitor.id, monitor.url, exc)
        monitor.last_checked_at = now
        monitor.next_check_at = now + timedelta(minutes=monitor.frequency_minutes)
        session.add(monitor)
        session.commit()
        return

    events = _diff_events(monitor.id, monitor.last_result, result)
    for event in events:
        session.add(event)

    _deliver_events(session, monitor, events, now)

    monitor.last_result = result.model_dump(mode="json")
    monitor.last_checked_at = now
    monitor.next_check_at = now + timedelta(minutes=monitor.frequency_minutes)
    session.add(monitor)
    session.commit()
