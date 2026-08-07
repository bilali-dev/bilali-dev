from __future__ import annotations

from pathlib import Path

import pytest

from app.errors import UnsupportedMarketplaceError
from app.models import ExtractionResult
from app.services.extractor import extract_from_html, find_adapter

FIXTURE = Path(__file__).parent / "fixtures" / "erli_product_sample.html"
SOURCE_URL = "https://erli.pl/produkt/demo,123"


def _load_result() -> ExtractionResult:
    html = FIXTURE.read_text(encoding="utf-8")
    return extract_from_html(html, SOURCE_URL)


def test_parses_sample_fixture() -> None:
    result = _load_result()

    assert result.marketplace == "erli"
    assert result.seller.name == "Demo Meble Sp. z o.o."
    assert result.seller.tax_id == "1234567890"
    assert result.seller.rating == 4.8
    assert result.seller.reviews_count == 725


def test_parses_product_price_and_currency() -> None:
    result = _load_result()

    assert result.product.title == "Szafka łazienkowa Demo 50 cm"
    assert result.product.price == 149.9
    assert result.product.currency == "PLN"


def test_resolves_relative_store_url() -> None:
    result = _load_result()

    assert str(result.seller.store_url) == "https://erli.pl/sprzedawca/demo-meble"


def test_missing_fields_do_not_crash() -> None:
    html = "<html><body><h1 data-testid='product-title'>Produto sem vendedor</h1></body></html>"
    result = extract_from_html(html, SOURCE_URL)

    assert result.seller.name is None
    assert result.seller.rating is None
    assert "Could not find seller name. Inspect the saved HTML." in result.warnings


def test_unsupported_marketplace_raises() -> None:
    with pytest.raises(UnsupportedMarketplaceError):
        find_adapter("https://example.com/produto/1")


def test_price_with_thousands_separator() -> None:
    html = "<html><body><div data-testid='product-price'>1 249,90 PLN</div></body></html>"
    result = extract_from_html(html, SOURCE_URL)

    assert result.product.price == 1249.9
    assert result.product.currency == "PLN"
