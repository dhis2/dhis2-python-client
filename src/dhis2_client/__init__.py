"""dhis2_client: Async + Sync DHIS2 clients with Pydantic v2 models and paging helpers."""

from .async_client import DHIS2AsyncClient
from .logging_conf import configure_logging
from .settings import Settings
from .sync_client import DHIS2Client

__all__ = ["DHIS2AsyncClient", "DHIS2Client", "Settings", "configure_logging"]
__version__ = "0.3.0"
