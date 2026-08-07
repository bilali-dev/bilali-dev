from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class SellerData(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    reviews_count: int | None = Field(default=None, ge=0)
    store_url: HttpUrl | None = None


class ProductData(BaseModel):
    title: str | None = None
    price: float | None = Field(default=None, ge=0)
    currency: str | None = None
    availability: str | None = None


class ExtractionResult(BaseModel):
    marketplace: str
    source_url: HttpUrl
    product: ProductData
    seller: SellerData
    warnings: list[str] = Field(default_factory=list)
