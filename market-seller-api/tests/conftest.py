from __future__ import annotations

import os
from pathlib import Path

_TEST_DB_PATH = Path(__file__).parent / "test_market_seller_api.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")

import pytest
from sqlmodel import SQLModel

from app.db import engine, init_db


@pytest.fixture(autouse=True)
def _reset_database():
    SQLModel.metadata.drop_all(engine)
    init_db()
    yield
