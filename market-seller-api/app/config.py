import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    user_agent: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (compatible; MarketSellerAPI/0.1; +https://example.com/bot)",
    )
    max_body_size_bytes: int = int(os.getenv("MAX_BODY_SIZE_BYTES", str(1_000_000)))


settings = Settings()
