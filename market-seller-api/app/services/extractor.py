from __future__ import annotations

from app.adapters.base import MarketplaceAdapter
from app.adapters.erli import ErliAdapter
from app.errors import ParsePageError, UnsupportedMarketplaceError
from app.models import ExtractionResult
from app.services.fetcher import fetch_html

ADAPTERS: tuple[MarketplaceAdapter, ...] = (ErliAdapter(),)


def find_adapter(url: str) -> MarketplaceAdapter:
    for adapter in ADAPTERS:
        if adapter.supports(url):
            return adapter
    raise UnsupportedMarketplaceError(f"No adapter supports this URL: {url}")


def extract_from_html(html: str, source_url: str) -> ExtractionResult:
    adapter = find_adapter(source_url)
    try:
        return adapter.parse(html, source_url)
    except UnsupportedMarketplaceError:
        raise
    except Exception as exc:
        raise ParsePageError(
            f"Failed to parse page with {adapter.name} adapter: {exc}"
        ) from exc


def extract_from_url(url: str) -> ExtractionResult:
    find_adapter(url)
    html = fetch_html(url)
    return extract_from_html(html, url)
