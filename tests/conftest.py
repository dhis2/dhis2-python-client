import json
import os
import warnings
from pathlib import Path

import pytest
from dotenv import load_dotenv

# 1) Auto-load environment variables from .env at repo root
load_dotenv()

# 2) Warn if destructive integration tests are enabled
if os.environ.get("DHIS2_ALLOW_MUTATIONS", "").strip().lower() in {"1", "true", "yes"}:
    warnings.warn(
        "⚠️  DHIS2_ALLOW_MUTATIONS is enabled — integration tests may CREATE/UPDATE/DELETE data! "
        "Point to a safe test instance (not production).",
        RuntimeWarning,
        stacklevel=1,
    )

# 3) Global fixture loader for files under tests/fixtures/
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fx():
    """Fixture helper for loading test assets from tests/fixtures/."""

    class _Fx:
        dir = FIXTURES_DIR

        def path(self, name: str) -> Path:
            return FIXTURES_DIR / name

        def text(self, name: str, encoding: str = "utf-8") -> str:
            return (FIXTURES_DIR / name).read_text(encoding=encoding)

        def json(self, name: str, encoding: str = "utf-8"):
            return json.loads((FIXTURES_DIR / name).read_text(encoding=encoding))

    return _Fx()
