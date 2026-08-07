from __future__ import annotations

import hashlib
import hmac
import json

import httpx


def sign_payload(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def send_webhook(url: str, secret: str, event: dict) -> bool:
    body = json.dumps(event, default=str).encode("utf-8")
    signature = sign_payload(secret, body)
    try:
        response = httpx.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature-256": signature,
            },
            timeout=10.0,
        )
        return response.status_code < 400
    except httpx.HTTPError:
        return False
