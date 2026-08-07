from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import get_current_customer
from app.config import settings
from app.db import get_session
from app.db_models import Customer
from app.plans import PLANS

router = APIRouter()

_PRICE_IDS = {
    "starter": settings.stripe_price_starter,
    "pro": settings.stripe_price_pro,
}


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/v1/billing/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    payload: CheckoutRequest,
    customer: Customer = Depends(get_current_customer),
) -> CheckoutResponse:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=501, detail="Billing is not configured on this server.")
    if payload.plan not in PLANS or payload.plan == "free":
        raise HTTPException(status_code=400, detail="Unknown plan.")

    price_id = _PRICE_IDS.get(payload.plan)
    if not price_id:
        raise HTTPException(
            status_code=500, detail=f"No Stripe price configured for plan '{payload.plan}'."
        )

    stripe.api_key = settings.stripe_secret_key
    checkout_session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
        customer_email=customer.email,
        client_reference_id=customer.id,
        metadata={"plan": payload.plan, "customer_id": customer.id},
    )
    return CheckoutResponse(checkout_url=checkout_session.url)


@router.post("/v1/billing/webhook")
async def stripe_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=501, detail="Billing webhook is not configured on this server."
        )

    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.") from exc

    _handle_stripe_event(session, event)
    return {"received": True}


def _handle_stripe_event(session: Session, event: dict) -> None:
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        customer_id = data.get("client_reference_id") or data.get("metadata", {}).get(
            "customer_id"
        )
        plan = data.get("metadata", {}).get("plan")
        customer = session.get(Customer, customer_id) if customer_id else None
        if customer:
            customer.stripe_customer_id = data.get("customer")
            customer.stripe_subscription_id = data.get("subscription")
            if plan in PLANS:
                customer.plan = plan
            session.add(customer)
            session.commit()

    elif event_type == "customer.subscription.deleted":
        stripe_customer_id = data.get("customer")
        customer = session.exec(
            select(Customer).where(Customer.stripe_customer_id == stripe_customer_id)
        ).first()
        if customer:
            customer.plan = "free"
            session.add(customer)
            session.commit()
