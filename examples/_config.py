from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dhis2_client import DHIS2Client
from dhis2_client.settings import ClientSettings


def _load_dotenv(path: Optional[str] = None) -> None:
    """
    Load env vars from a .env file, defaulting to repo root `.env`.
    Existing environment variables take precedence.
    """
    candidates = []
    if path:
        candidates.append(Path(path))
    # prefer repo root .env
    candidates += [Path(".env")]

    p = next((c for c in candidates if c.exists()), None)
    if not p:
        return

    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def make_client(dotenv_path: Optional[str] = None) -> DHIS2Client:
    _load_dotenv(dotenv_path)

    base_url = os.getenv("DHIS2_BASE_URL")
    token = os.getenv("DHIS2_TOKEN")
    username = os.getenv("DHIS2_USERNAME")
    password = os.getenv("DHIS2_PASSWORD")

    if not base_url:
        raise RuntimeError("Missing DHIS2_BASE_URL (set in root .env or shell env).")
    if not token and (not username or not password):
        raise RuntimeError("Set DHIS2_TOKEN or DHIS2_USERNAME + DHIS2_PASSWORD (root .env or shell env).")

    cfg = ClientSettings(
        base_url=base_url,
        token=token,
        username=username if not token else None,
        password=password if not token else None,
        log_level=os.getenv("DHIS2_LOG_LEVEL", "INFO"),
        log_destination=os.getenv("DHIS2_LOG_DESTINATION", "stdout"),
    )
    return DHIS2Client(settings=cfg)
