from __future__ import annotations

import logging
import os
import sys

import structlog

_VALID_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

def _coerce_level(name_or_none: str | None) -> int:
    # Priority: explicit arg -> DHIS2_LOG_LEVEL env -> WARNING default
    raw = (name_or_none or os.getenv("DHIS2_LOG_LEVEL") or "WARNING").upper().strip()
    return _VALID_LEVELS.get(raw, logging.WARNING)

def configure_logging(
    level: str | None = None,
    *,
    include_httpx: bool = False,
    include_respx: bool = False,
) -> structlog.stdlib.BoundLogger:
    """
    Configure structlog+logging.
    - default level: WARNING
    - override by: level param (wins) or LOG_LEVEL env
    - optional: include_httpx / include_respx
    """
    numeric_level = _coerce_level(level)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(stream=sys.stdout, level=numeric_level)

    if include_httpx:
        logging.getLogger("httpx").setLevel(numeric_level)
    if include_respx:
        logging.getLogger("respx").setLevel(numeric_level)

    return structlog.get_logger("dhis2_client")
