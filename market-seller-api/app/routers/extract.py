from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator
from sqlmodel import Session

from app.auth import get_current_customer
from app.config import settings
from app.db import get_session
from app.db_models import Customer, UsageEvent
from app.errors import FetchPageError, ParsePageError, UnsupportedMarketplaceError
from app.models import ExtractionResult
from app.plans import plan_for, usage_this_month
from app.rate_limit import enforce_rate_limit
from app.services.extractor import extract_from_url

router = APIRouter()

ALLOWED_SCHEMES = {"http", "https"}


class ExtractRequest(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validate_scheme(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme not in ALLOWED_SCHEMES:
            raise ValueError("Only http and https URLs are supported.")
        return value


@router.post("/v1/extract", response_model=ExtractionResult)
def extract(
    payload: ExtractRequest,
    customer: Customer = Depends(get_current_customer),
    session: Session = Depends(get_session),
) -> ExtractionResult:
    enforce_rate_limit(customer.id, settings.rate_limit_per_minute)

    plan = plan_for(customer.plan)
    used = usage_this_month(session, customer.id)
    if used >= plan.monthly_results:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Monthly quota exceeded for the '{plan.name}' plan "
                f"({plan.monthly_results} results)."
            ),
        )

    url = str(payload.url)
    marketplace: str | None = None
    success = False
    try:
        result = extract_from_url(url)
        marketplace = result.marketplace
        success = True
        return result
    except UnsupportedMarketplaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (FetchPageError, ParsePageError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        session.add(
            UsageEvent(
                customer_id=customer.id,
                endpoint="/v1/extract",
                marketplace=marketplace,
                success=success,
                cost_units=1,
            )
        )
        session.commit()
