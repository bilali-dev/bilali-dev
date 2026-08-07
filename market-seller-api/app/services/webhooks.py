from __future__ import annotations

import hashlib
import hmac
import json
import time

import httpx

MAX_ATTEMPTS = 3
# Delay before attempt 2 and attempt 3, respectively.
BACKOFF_SECONDS = (1.0, 3.0)


def sign_payload(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _post_once(url: str, secret: str, event: dict) -> tuple[bool, str | None]:
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
        if response.status_code < 400:
            return True, None
        return False, f"HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        return False, str(exc)


def send_webhook_with_retry(url: str, secret: str, event: dict) -> tuple[bool, int, str | None]:
    """Deliver a webhook with bounded retries and backoff.

    Returns (success, attempts_made, last_error). Never raises — a delivery
    failure after MAX_ATTEMPTS is reported to the caller, not thrown.
    """
    last_error: str | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        success, error = _post_once(url, secret, event)
        if success:
            return True, attempt, None
        last_error = error
        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_SECONDS[attempt - 1])
    return False, MAX_ATTEMPTS, last_error
