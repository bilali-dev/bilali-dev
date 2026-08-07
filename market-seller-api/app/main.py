from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator

from app.errors import FetchPageError, ParsePageError, UnsupportedMarketplaceError
from app.models import ExtractionResult
from app.services.extractor import extract_from_url

app = FastAPI(title="Marketplace Seller API", version="0.1.0")

ALLOWED_SCHEMES = {"http", "https"}


class ExtractRequest(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validate_scheme(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme not in ALLOWED_SCHEMES:
            raise ValueError("Only http and https URLs are supported.")
        return value


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/extract", response_model=ExtractionResult)
def extract(payload: ExtractRequest) -> ExtractionResult:
    url = str(payload.url)
    try:
        return extract_from_url(url)
    except UnsupportedMarketplaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (FetchPageError, ParsePageError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
