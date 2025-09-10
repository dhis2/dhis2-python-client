from __future__ import annotations

import logging
import os
import sys

import structlog

# Accepted log levels (validated; anything else -> WARNING)
VALID_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


def configure_logging(level: str | None = None, include_httpx: bool = False):
    """
    Configure JSON logging using structlog.

    Priority:
      1) explicit `level` argument
      2) LOG_LEVEL environment variable
      3) default: WARNING

    Valid levels: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET.
    Invalid values fall back to WARNING.

    Args:
        level: Desired log level name (e.g., "INFO").
        include_httpx: If True, also set httpx/respx logger levels.

    Returns:
        A structlog BoundLogger for "dhis2_client".
    """
    level_name = (level or os.getenv("LOG_LEVEL", "WARNING")).upper()
    log_level = VALID_LEVELS.get(level_name, logging.WARNING)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib root logger
    logging.basicConfig(stream=sys.stdout, level=log_level)

    if include_httpx:
        logging.getLogger("httpx").setLevel(log_level)
        logging.getLogger("respx").setLevel(log_level)

    return structlog.get_logger("dhis2_client")


# Global module logger (imported by client)
logger = configure_logging()
