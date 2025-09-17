"""dhis2_client: Async + Sync DHIS2 clients with Pydantic v2 models and paging helpers."""
"""
from .async_client import DHIS2AsyncClient
from .logging_conf import configure_logging
from .settings import Settings
from .sync_client import DHIS2Client

__all__ = ["DHIS2AsyncClient", "DHIS2Client", "Settings", "configure_logging"]
__version__ = "0.3.0"

"""

from typing import Any

__all__ = ["DHIS2Client", "DHIS2AsyncClient", "Settings"]

def __getattr__(name: str) -> Any:
    # Lazy imports so importing dhis2_client doesn't pull httpx (and its CLI) immediately.
    if name == "DHIS2Client":
        from .sync_client import DHIS2Client  # type: ignore
        return DHIS2Client
    if name == "DHIS2AsyncClient":
        # async_client imports httpx; defer until actually requested
        from .async_client import DHIS2AsyncClient  # type: ignore
        return DHIS2AsyncClient
    if name == "Settings":
        from .settings import Settings  # type: ignore
        return Settings
    raise AttributeError(f"module 'dhis2_client' has no attribute {name!r}")