# tests/integration/_env.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def load_dotenv(path: Optional[str] = None) -> None:
    """
    Minimal .env loader for tests.
    Precedence: existing env vars > .env file.
    Looks for:
      - explicit path
      - ./tests/integration/.env
      - ./tests/.env
      - ./.env
    """
    candidates = []
    if path:
        candidates.append(Path(path))
    candidates += [
        Path("tests/integration/.env"),
        Path("tests/.env"),
        Path(".env"),
    ]

    p = next((c for c in candidates if c.exists()), None)
    if not p:
        return

    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)
