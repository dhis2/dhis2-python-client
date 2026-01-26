from __future__ import annotations

import os
from pathlib import Path
import pytest

from dhis2_client import DHIS2Client
from dhis2_client.settings import ClientSettings


def load_dotenv() -> None:
    for p in (Path("tests/integration/.env"), Path("tests/.env"), Path(".env")):
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        break


@pytest.fixture(scope="session")
def live_settings() -> ClientSettings:
    load_dotenv()

    base_url = os.getenv("DHIS2_BASE_URL")
    token = os.getenv("DHIS2_TOKEN")
    username = os.getenv("DHIS2_USERNAME")
    password = os.getenv("DHIS2_PASSWORD")

    if not base_url or not (token or (username and password)):
        pytest.skip("Set DHIS2_BASE_URL and either DHIS2_TOKEN or DHIS2_USERNAME/DHIS2_PASSWORD.")

    return ClientSettings(
        base_url=base_url,
        token=token,
        username=username if not token else None,
        password=password if not token else None,
        log_level=os.getenv("DHIS2_LOG_LEVEL", "INFO"),
        log_destination=os.getenv("DHIS2_LOG_DESTINATION", "stdout"),
    )


@pytest.fixture(scope="session")
def live_client(live_settings: ClientSettings) -> DHIS2Client:
    return DHIS2Client(settings=live_settings)


@pytest.fixture(scope="session")
def allow_mutations() -> bool:
    return os.getenv("DHIS2_ALLOW_MUTATIONS", "").lower() in {"1", "true", "yes"}
