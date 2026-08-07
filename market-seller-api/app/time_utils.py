from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Naive UTC timestamp.

    SQLite silently drops timezone info on round-trip while Postgres keeps it,
    which makes tz-aware vs. naive comparisons blow up depending on which
    database is behind DATABASE_URL. Storing and comparing naive UTC
    everywhere sidesteps that: every value in this codebase is UTC by
    convention, on both backends.
    """
    return datetime.now(UTC).replace(tzinfo=None)
