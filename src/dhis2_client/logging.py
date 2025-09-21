from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Build a stable JSON envelope; avoid serializing extras that might fail.
        payload = {
            "ts": datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include pathname:lineno when DEBUG to aid troubleshooting
        if record.levelno <= logging.DEBUG:
            payload["file"] = f"{os.path.basename(record.pathname)}:{record.lineno}"
            payload["func"] = record.funcName
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger("dhis2_client")
# Do not attach handlers at import time; let configure_logging control it.
logger.propagate = False  # keep logs from duplicating through root


def _dest_to_handler(destination: Optional[str]) -> logging.Handler:
    """
    Map destination hint to a logging.Handler.
    - None or "stderr" -> StreamHandler(sys.stderr)
    - "stdout" -> StreamHandler(sys.stdout)
    - anything else -> FileHandler(path)
    """
    if destination in (None, "stderr"):
        return logging.StreamHandler(stream=sys.stderr)
    if destination == "stdout":
        return logging.StreamHandler(stream=sys.stdout)
    # File path
    return logging.FileHandler(destination, encoding="utf-8")


def configure_logging(
    *,
    level: str = "WARNING",
    fmt: str = "json",
    destination: Optional[str] = None,
) -> None:
    """
    Configure the library logger. Safe to call multiple times; it will replace handlers.
    """
    # Normalize/validate level
    lvl = getattr(logging, str(level).upper(), logging.WARNING)
    logger.setLevel(lvl)

    # Reset handlers to avoid duplicates when reconfiguring
    for h in list(logger.handlers):
        logger.removeHandler(h)

    handler = _dest_to_handler(destination)

    if fmt == "text":
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    else:
        formatter = JsonFormatter()

    handler.setFormatter(formatter)
    logger.addHandler(handler)
