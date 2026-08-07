from __future__ import annotations

import csv
from pathlib import Path

from app.models import ExtractionResult

CSV_FIELDS = (
    "marketplace",
    "source_url",
    "product_title",
    "price",
    "currency",
    "seller_name",
    "tax_id",
    "address",
    "rating",
    "reviews_count",
    "store_url",
)


def save_json(result: ExtractionResult, path: Path, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    indent = 2 if pretty else None
    path.write_text(result.model_dump_json(indent=indent), encoding="utf-8")


def _row_from_result(result: ExtractionResult) -> dict:
    return {
        "marketplace": result.marketplace,
        "source_url": str(result.source_url),
        "product_title": result.product.title,
        "price": result.product.price,
        "currency": result.product.currency,
        "seller_name": result.seller.name,
        "tax_id": result.seller.tax_id,
        "address": result.seller.address,
        "rating": result.seller.rating,
        "reviews_count": result.seller.reviews_count,
        "store_url": str(result.seller.store_url) if result.seller.store_url else None,
    }


def save_csv(results: list[ExtractionResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow(_row_from_result(result))
