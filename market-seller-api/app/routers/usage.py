from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.auth import get_current_customer
from app.db import get_session
from app.db_models import Customer
from app.plans import plan_for, usage_this_month

router = APIRouter()


class UsageResponse(BaseModel):
    plan: str
    monthly_limit: int
    used_this_month: int
    remaining: int


@router.get("/v1/usage", response_model=UsageResponse)
def usage(
    customer: Customer = Depends(get_current_customer),
    session: Session = Depends(get_session),
) -> UsageResponse:
    plan = plan_for(customer.plan)
    used = usage_this_month(session, customer.id)
    return UsageResponse(
        plan=plan.name,
        monthly_limit=plan.monthly_results,
        used_this_month=used,
        remaining=max(plan.monthly_results - used, 0),
    )
