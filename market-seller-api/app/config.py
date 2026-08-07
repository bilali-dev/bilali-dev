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

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./market_seller_api.db")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret-change-me")
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_price_starter: str = os.getenv("STRIPE_PRICE_STARTER", "")
    stripe_price_pro: str = os.getenv("STRIPE_PRICE_PRO", "")


settings = Settings()
