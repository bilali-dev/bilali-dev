from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from app.auth import generate_api_key
from app.db import get_session
from app.db_models import ApiKey, Customer

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr


class SignupResponse(BaseModel):
    customer_id: str
    email: str
    plan: str
    api_key: str


@router.post("/v1/signup", response_model=SignupResponse, status_code=201)
def signup(
    payload: SignupRequest,
    session: Session = Depends(get_session),
) -> SignupResponse:
    existing = session.exec(select(Customer).where(Customer.email == payload.email)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered.")

    customer = Customer(email=payload.email, plan="free")
    session.add(customer)
    session.commit()
    session.refresh(customer)

    raw_key, prefix, key_hash = generate_api_key()
    session.add(ApiKey(customer_id=customer.id, prefix=prefix, key_hash=key_hash))
    session.commit()

    return SignupResponse(
        customer_id=customer.id,
        email=customer.email,
        plan=customer.plan,
        api_key=raw_key,
    )
