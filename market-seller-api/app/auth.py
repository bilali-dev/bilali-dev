from __future__ import annotations

import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.db_models import ApiKey, Customer

KEY_PREFIX_LENGTH = 12


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_key, prefix, key_hash). Only the hash is persisted."""
    raw_key = f"sk_live_{secrets.token_urlsafe(32)}"
    prefix = raw_key[:KEY_PREFIX_LENGTH]
    return raw_key, prefix, _hash_key(raw_key)


def get_current_customer(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> Customer:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    raw_key = authorization.removeprefix("Bearer ").strip()
    prefix = raw_key[:KEY_PREFIX_LENGTH]
    key_hash = _hash_key(raw_key)

    api_key = session.exec(
        select(ApiKey).where(ApiKey.prefix == prefix, ApiKey.active == True)
    ).first()

    if api_key is None or not secrets.compare_digest(api_key.key_hash, key_hash):
        raise HTTPException(status_code=401, detail="Invalid API key.")

    customer = session.get(Customer, api_key.customer_id)
    if customer is None:
        raise HTTPException(status_code=401, detail="Invalid API key.")

    return customer
