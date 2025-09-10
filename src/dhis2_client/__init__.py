"""dhis2_client: Async DHIS2 client with Pydantic v2 models and paging helpers."""

from .client import DHIS2AsyncClient
from .settings import Settings

__all__ = ["DHIS2AsyncClient", "Settings"]

__version__ = "0.3.0"
