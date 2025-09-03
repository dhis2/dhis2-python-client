from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DataElement(BaseModel):
    """DHIS2 DataElement model subset used by tests and convenience methods."""

    model_config = ConfigDict(extra="ignore")
    id: Optional[str] = None
    name: str
    shortName: Optional[str] = None  # noqa: N815
    domainType: Optional[str] = Field(default="AGGREGATE")  # noqa: N815
    valueType: Optional[str] = None  # noqa: N815
    aggregationType: Optional[str] = None  # noqa: N815
