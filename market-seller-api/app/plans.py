from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, func, select

from app.db_models import Monitor, UsageEvent
from app.time_utils import utcnow


@dataclass(frozen=True)
class Plan:
    name: str
    monthly_results: int
    max_monitors: int
    min_frequency_minutes: int


PLANS: dict[str, Plan] = {
    "free": Plan(name="free", monthly_results=50, max_monitors=0, min_frequency_minutes=0),
    "starter": Plan(name="starter", monthly_results=1000, max_monitors=10, min_frequency_minutes=1440),
    "pro": Plan(name="pro", monthly_results=10_000, max_monitors=100, min_frequency_minutes=60),
}


def plan_for(customer_plan: str) -> Plan:
    return PLANS.get(customer_plan, PLANS["free"])


def usage_this_month(session: Session, customer_id: str) -> int:
    now = utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    statement = select(func.count(UsageEvent.id)).where(
        UsageEvent.customer_id == customer_id,
        UsageEvent.success == True,
        UsageEvent.created_at >= month_start,
    )
    return session.exec(statement).one()


def monitors_count(session: Session, customer_id: str) -> int:
    statement = select(func.count(Monitor.id)).where(Monitor.customer_id == customer_id)
    return session.exec(statement).one()
