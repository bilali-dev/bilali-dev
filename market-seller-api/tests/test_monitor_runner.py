from __future__ import annotations

from app.models import ExtractionResult, ProductData, SellerData
from app.services.monitor_runner import _diff_events


def _result(price: float) -> ExtractionResult:
    return ExtractionResult(
        marketplace="erli",
        source_url="https://erli.pl/produkt/demo,123",
        product=ProductData(title="Demo", price=price, currency="PLN", availability="Dostępny"),
        seller=SellerData(name="Demo Meble", rating=4.8, reviews_count=725),
    )


def test_no_events_when_no_previous_result() -> None:
    events = _diff_events("mon_1", None, _result(149.9))

    assert events == []


def test_price_change_is_detected() -> None:
    previous = _result(149.9).model_dump(mode="json")

    events = _diff_events("mon_1", previous, _result(139.9))

    assert len(events) == 1
    assert events[0].event_type == "product.price_changed"
    assert events[0].previous_value == "149.9"
    assert events[0].current_value == "139.9"


def test_no_events_when_nothing_changed() -> None:
    previous = _result(149.9).model_dump(mode="json")

    events = _diff_events("mon_1", previous, _result(149.9))

    assert events == []
