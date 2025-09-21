from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

LogFormat = Literal["json", "text"]
LogDestination = Optional[
    Literal["stdout", "stderr"]
]  # or a filesystem path (str) via type: ignore


@dataclass
class ClientSettings:
    """
    Centralized configuration for DHIS2Client.

    Pass an instance of this to DHIS2Client(settings=...) to apply defaults.
    Any explicit keyword args to DHIS2Client(...) will override these.
    """

    # --- Connection / auth ---
    base_url: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None  # "ApiToken ..." or "Bearer ..." or raw token

    # --- HTTP behavior ---
    default_page_size: int = 50
    timeout: float = 30.0
    retries: int = 3
    verify_ssl: bool = True

    # --- Logging ---
    log_level: str = "WARNING"  # "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
    log_format: LogFormat = "json"  # "json" (default) or "text"
    log_destination: str | None = None
    # None or "stderr" -> stderr, "stdout" -> stdout, any other string -> treated as a file path.

    # --- Future mode flag (reserved) ---
    model_mode: str = "raw"  # keep for forward compatibility (e.g., "pydantic" later)
