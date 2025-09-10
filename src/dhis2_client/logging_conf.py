# src/dhis2_client/logging_conf.py
from __future__ import annotations

import logging
import os
import sys

import structlog


def configure_logging(
    level: str | None = None,
    *,
    include_httpx: bool = False,
    force: bool = False,
):
    """
    Configure JSON logging using structlog.

    - Default level: WARNING (unless overridden by arg or LOG_LEVEL env).
    - include_httpx=True also applies the level to httpx/httpcore/respx.
    - force=True reconfigures even if logging was already set up.
    """
    level_name = (level or os.getenv("LOG_LEVEL") or "WARNING").upper()
    numeric = getattr(logging, level_name, logging.WARNING)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        stream=sys.stdout,
        level=numeric,
        force=force,
    )

    if include_httpx:
        for name in ("httpx", "httpcore", "respx"):
            logging.getLogger(name).setLevel(numeric)

    # Return a library-scoped logger for convenience if you want it here.
    return structlog.get_logger("dhis2_client")
