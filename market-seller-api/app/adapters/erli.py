from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.adapters.base import MarketplaceAdapter
from app.models import ExtractionResult, ProductData, SellerData

SELECTORS: dict[str, tuple[str, ...]] = {
    "product_title": (
        "[data-testid='product-title']",
        "h1[itemprop='name']",
        "h1",
    ),
    "product_price": (
        "[data-testid='product-price']",
        "[itemprop='price']",
        ".price",
    ),
    "product_availability": (
        "[data-testid='product-availability']",
        ".availability",
    ),
    "seller_name": (
        "[data-testid='seller-name']",
        "[itemprop='seller']",
        ".seller-name",
    ),
    "seller_tax_id": (
        "[data-testid='seller-tax-id']",
        ".seller-nip",
    ),
    "seller_address": (
        "[data-testid='seller-address']",
        ".seller-address",
    ),
    "seller_rating": (
        "[data-testid='seller-rating']",
        ".seller-rating",
    ),
    "seller_reviews_count": (
        "[data-testid='seller-reviews-count']",
        ".seller-reviews-count",
    ),
    "seller_store_link": (
        "[data-testid='seller-store-link']",
        "a.seller-store-link",
    ),
}

_CURRENCY_SYMBOLS = {"zł": "PLN", "€": "EUR", "$": "USD", "£": "GBP"}


def text_from_selectors(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            value = element.get_text(" ", strip=True)
            if value:
                return value
    return None


def href_from_selectors(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        element = soup.select_one(selector)
        if element and element.has_attr("href"):
            href = element["href"].strip()
            if href:
                return href
    return None


def parse_tax_id(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return digits or None


def parse_rating(raw: str | None) -> float | None:
    if not raw:
        return None
    match = re.search(r"(\d+[.,]?\d*)", raw)
    if not match:
        return None
    try:
        rating = float(match.group(1).replace(",", "."))
    except ValueError:
        return None
    if rating < 0 or rating > 5:
        return None
    return rating


def parse_reviews_count(raw: str | None) -> int | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return int(digits) if digits else None


def parse_price(raw: str | None) -> tuple[float | None, str | None]:
    if not raw:
        return None, None

    currency = None
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in raw:
            currency = code
            break
    if currency is None:
        code_match = re.search(r"\b[A-Z]{3}\b", raw)
        if code_match:
            currency = code_match.group(0)

    number_match = re.search(r"[\d.,\s ]*\d", raw)
    if not number_match:
        return None, currency

    number_text = number_match.group(0).replace(" ", "").replace(" ", "")

    if "," in number_text and "." in number_text:
        number_text = number_text.replace(".", "").replace(",", ".")
    elif "," in number_text:
        number_text = number_text.replace(",", ".")

    try:
        price = float(number_text)
    except ValueError:
        return None, currency

    return price, currency


class ErliAdapter(MarketplaceAdapter):
    name = "erli"

    def supports(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return host == "erli.pl" or host.endswith(".erli.pl")

    def parse(self, html: str, source_url: str) -> ExtractionResult:
        soup = BeautifulSoup(html, "html.parser")
        warnings: list[str] = []

        title = text_from_selectors(soup, SELECTORS["product_title"])
        if title is None:
            warnings.append("Could not find product title. Inspect the saved HTML.")

        raw_price = text_from_selectors(soup, SELECTORS["product_price"])
        price, currency = parse_price(raw_price)
        if price is None:
            warnings.append("Could not find product price. Inspect the saved HTML.")

        availability = text_from_selectors(soup, SELECTORS["product_availability"])

        seller_name = text_from_selectors(soup, SELECTORS["seller_name"])
        if seller_name is None:
            warnings.append("Could not find seller name. Inspect the saved HTML.")

        tax_id = parse_tax_id(text_from_selectors(soup, SELECTORS["seller_tax_id"]))

        address = text_from_selectors(soup, SELECTORS["seller_address"])
        if address is None:
            warnings.append("Could not find seller address. Inspect the saved HTML.")

        rating = parse_rating(text_from_selectors(soup, SELECTORS["seller_rating"]))
        reviews_count = parse_reviews_count(
            text_from_selectors(soup, SELECTORS["seller_reviews_count"])
        )

        store_href = href_from_selectors(soup, SELECTORS["seller_store_link"])
        store_url = urljoin(source_url, store_href) if store_href else None

        product = ProductData(
            title=title,
            price=price,
            currency=currency,
            availability=availability,
        )
        seller = SellerData(
            name=seller_name,
            tax_id=tax_id,
            address=address,
            rating=rating,
            reviews_count=reviews_count,
            store_url=store_url,
        )

        return ExtractionResult(
            marketplace=self.name,
            source_url=source_url,
            product=product,
            seller=seller,
            warnings=warnings,
        )
