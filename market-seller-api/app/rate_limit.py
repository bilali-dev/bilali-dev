from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException

_WINDOW_SECONDS = 60.0
_requests: dict[str, deque[float]] = defaultdict(deque)


def enforce_rate_limit(key: str, limit_per_minute: int) -> None:
    """In-process sliding-window limiter. Fine for a single instance;
    a multi-instance deployment needs a shared store such as Redis."""
    now = time.monotonic()
    window = _requests[key]
    while window and now - window[0] > _WINDOW_SECONDS:
        window.popleft()
    if len(window) >= limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    window.append(now)
