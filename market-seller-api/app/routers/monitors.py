from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlmodel import Session, select

from app.auth import get_current_customer
from app.db import get_session
from app.db_models import Customer, Monitor
from app.plans import monitors_count, plan_for
from app.time_utils import utcnow

router = APIRouter()


class MonitorCreateRequest(BaseModel):
    url: HttpUrl
    frequency_minutes: int = 1440
    webhook_url: HttpUrl | None = None


class MonitorResponse(BaseModel):
    id: str
    url: str
    frequency_minutes: int
    webhook_url: str | None
    status: str
    last_checked_at: datetime | None
    next_check_at: datetime


def _to_response(monitor: Monitor) -> MonitorResponse:
    return MonitorResponse(
        id=monitor.id,
        url=monitor.url,
        frequency_minutes=monitor.frequency_minutes,
        webhook_url=monitor.webhook_url,
        status=monitor.status,
        last_checked_at=monitor.last_checked_at,
        next_check_at=monitor.next_check_at,
    )


def _get_owned_monitor(session: Session, customer: Customer, monitor_id: str) -> Monitor:
    monitor = session.get(Monitor, monitor_id)
    if monitor is None or monitor.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Monitor not found.")
    return monitor


@router.post("/v1/monitors", response_model=MonitorResponse, status_code=201)
def create_monitor(
    payload: MonitorCreateRequest,
    customer: Customer = Depends(get_current_customer),
    session: Session = Depends(get_session),
) -> MonitorResponse:
    plan = plan_for(customer.plan)
    if plan.max_monitors == 0:
        raise HTTPException(
            status_code=402, detail=f"The '{plan.name}' plan does not include monitors."
        )
    if monitors_count(session, customer.id) >= plan.max_monitors:
        raise HTTPException(
            status_code=402, detail=f"Monitor limit reached for the '{plan.name}' plan."
        )
    if payload.frequency_minutes < plan.min_frequency_minutes:
        raise HTTPException(
            status_code=402,
            detail=(
                f"The '{plan.name}' plan requires frequency_minutes >= "
                f"{plan.min_frequency_minutes}."
            ),
        )

    monitor = Monitor(
        customer_id=customer.id,
        url=str(payload.url),
        frequency_minutes=payload.frequency_minutes,
        webhook_url=str(payload.webhook_url) if payload.webhook_url else None,
        next_check_at=utcnow(),
    )
    session.add(monitor)
    session.commit()
    session.refresh(monitor)
    return _to_response(monitor)


@router.get("/v1/monitors", response_model=list[MonitorResponse])
def list_monitors(
    customer: Customer = Depends(get_current_customer),
    session: Session = Depends(get_session),
) -> list[MonitorResponse]:
    monitors = session.exec(select(Monitor).where(Monitor.customer_id == customer.id)).all()
    return [_to_response(monitor) for monitor in monitors]


@router.get("/v1/monitors/{monitor_id}", response_model=MonitorResponse)
def get_monitor(
    monitor_id: str,
    customer: Customer = Depends(get_current_customer),
    session: Session = Depends(get_session),
) -> MonitorResponse:
    return _to_response(_get_owned_monitor(session, customer, monitor_id))


@router.delete("/v1/monitors/{monitor_id}", status_code=204)
def delete_monitor(
    monitor_id: str,
    customer: Customer = Depends(get_current_customer),
    session: Session = Depends(get_session),
) -> None:
    monitor = _get_owned_monitor(session, customer, monitor_id)
    session.delete(monitor)
    session.commit()
