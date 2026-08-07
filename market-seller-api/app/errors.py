class MarketplaceError(Exception):
    """Base error for all marketplace extraction failures."""


class UnsupportedMarketplaceError(MarketplaceError):
    """Raised when no adapter supports the given URL."""


class FetchPageError(MarketplaceError):
    """Raised when the page could not be downloaded."""


class ParsePageError(MarketplaceError):
    """Raised when the page was downloaded but could not be parsed."""
