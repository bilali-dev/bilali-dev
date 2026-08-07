from __future__ import annotations

import httpx

from app.services import webhooks


class _Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_signature_is_deterministic_hmac_sha256() -> None:
    signature = webhooks.sign_payload("secret", b'{"a":1}')

    assert signature == webhooks.sign_payload("secret", b'{"a":1}')
    assert len(signature) == 64


def test_different_secrets_produce_different_signatures() -> None:
    payload = b'{"a":1}'

    assert webhooks.sign_payload("secret-a", payload) != webhooks.sign_payload("secret-b", payload)


def test_succeeds_on_first_attempt(monkeypatch) -> None:
    monkeypatch.setattr(webhooks.httpx, "post", lambda *a, **k: _Response(200))

    success, attempts, error = webhooks.send_webhook_with_retry("https://x", "secret", {"a": 1})

    assert success is True
    assert attempts == 1
    assert error is None


def test_retries_then_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(webhooks.time, "sleep", lambda _seconds: None)
    responses = iter([_Response(500), _Response(503), _Response(200)])
    monkeypatch.setattr(webhooks.httpx, "post", lambda *a, **k: next(responses))

    success, attempts, error = webhooks.send_webhook_with_retry("https://x", "secret", {"a": 1})

    assert success is True
    assert attempts == 3
    assert error is None


def test_gives_up_after_max_attempts(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(webhooks.time, "sleep", sleeps.append)
    monkeypatch.setattr(webhooks.httpx, "post", lambda *a, **k: _Response(500))

    success, attempts, error = webhooks.send_webhook_with_retry("https://x", "secret", {"a": 1})

    assert success is False
    assert attempts == webhooks.MAX_ATTEMPTS
    assert error == "HTTP 500"
    assert len(sleeps) == webhooks.MAX_ATTEMPTS - 1


def test_network_error_is_caught_and_reported(monkeypatch) -> None:
    monkeypatch.setattr(webhooks.time, "sleep", lambda _seconds: None)

    def _raise(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(webhooks.httpx, "post", _raise)

    success, attempts, error = webhooks.send_webhook_with_retry("https://x", "secret", {"a": 1})

    assert success is False
    assert attempts == webhooks.MAX_ATTEMPTS
    assert "boom" in error
