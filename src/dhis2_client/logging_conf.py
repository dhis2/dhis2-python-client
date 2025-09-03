from __future__ import annotations

import logging
import os
import sys

import structlog


def configure_logging(level: str | None = None):
    """Configure JSON logging using structlog, honoring LOG_LEVEL env or provided level."""
    level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level_name, logging.INFO)),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(stream=sys.stdout, level=getattr(logging, level_name, logging.INFO))
    return structlog.get_logger("dhis2_client")


# Global module logger (imported by client)
logger = configure_logging()
