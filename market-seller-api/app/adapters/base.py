from abc import ABC, abstractmethod

from app.models import ExtractionResult


class MarketplaceAdapter(ABC):
    name: str

    @abstractmethod
    def supports(self, url: str) -> bool:
        ...

    @abstractmethod
    def parse(self, html: str, source_url: str) -> ExtractionResult:
        ...
