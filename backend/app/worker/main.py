"""APScheduler worker — P0 stub. Jobs added in P8."""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Worker started (P0 stub — no jobs yet)")
    # Keep container alive; jobs wired in P8
    while True:
        time.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    main()
