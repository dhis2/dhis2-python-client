from __future__ import annotations

from pydantic import BaseModel, ConfigDict, HttpUrl


class SystemInfo(BaseModel):
    """Subset of /api/system/info used by the client."""

    model_config = ConfigDict(extra="ignore")
    version: str
    contextPath: HttpUrl  # noqa: N815
    serverDate: str  # noqa: N815
