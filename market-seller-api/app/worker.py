from __future__ import annotations

import logging
import time

from sqlmodel import Session

from app.db import engine, init_db
from app.services.monitor_runner import run_due_monitors

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("worker")

POLL_INTERVAL_SECONDS = 60


def main() -> None:
    init_db()
    logger.info("Monitor worker started, polling every %ss", POLL_INTERVAL_SECONDS)
    while True:
        with Session(engine) as session:
            checked = run_due_monitors(session)
            if checked:
                logger.info("Checked %s due monitor(s)", checked)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
