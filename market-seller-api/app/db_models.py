from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _new_id() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Customer(SQLModel, table=True):
    id: str = Field(default_factory=_new_id, primary_key=True)
    email: str = Field(index=True, unique=True)
    plan: str = Field(default="free")
    created_at: datetime = Field(default_factory=_utcnow)
    stripe_customer_id: str | None = Field(default=None, index=True)
    stripe_subscription_id: str | None = None


class ApiKey(SQLModel, table=True):
    id: str = Field(default_factory=_new_id, primary_key=True)
    customer_id: str = Field(foreign_key="customer.id", index=True)
    prefix: str = Field(index=True)
    key_hash: str
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)


class Monitor(SQLModel, table=True):
    id: str = Field(default_factory=_new_id, primary_key=True)
    customer_id: str = Field(foreign_key="customer.id", index=True)
    url: str
    frequency_minutes: int = Field(default=1440)
    webhook_url: str | None = None
    status: str = Field(default="active")
    last_checked_at: datetime | None = None
    next_check_at: datetime = Field(default_factory=_utcnow, index=True)
    last_result: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utcnow)


class MonitorEvent(SQLModel, table=True):
    id: str = Field(default_factory=_new_id, primary_key=True)
    monitor_id: str = Field(foreign_key="monitor.id", index=True)
    event_type: str
    previous_value: str | None = None
    current_value: str | None = None
    created_at: datetime = Field(default_factory=_utcnow, index=True)


class UsageEvent(SQLModel, table=True):
    id: str = Field(default_factory=_new_id, primary_key=True)
    customer_id: str = Field(foreign_key="customer.id", index=True)
    endpoint: str
    marketplace: str | None = None
    success: bool
    cost_units: int = Field(default=1)
    created_at: datetime = Field(default_factory=_utcnow, index=True)
