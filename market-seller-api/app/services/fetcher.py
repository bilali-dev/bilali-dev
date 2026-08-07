from __future__ import annotations

import httpx

from app.config import settings
from app.errors import FetchPageError


def fetch_html(url: str) -> str:
    headers = {"User-Agent": settings.user_agent}
    try:
        with httpx.Client(
            headers=headers,
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.TimeoutException as exc:
        raise FetchPageError(f"Timed out fetching {url}") from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise FetchPageError(f"HTTP {status} while fetching {url}") from exc
    except httpx.HTTPError as exc:
        raise FetchPageError(f"Failed to fetch {url}: {exc}") from exc
