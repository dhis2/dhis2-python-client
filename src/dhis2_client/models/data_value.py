from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class DataValue(BaseModel):
    """Data value payload for /api/dataValueSets."""

    model_config = ConfigDict(extra="forbid")
    period: str
    value: str
    dataElement: str  # noqa: N815
    orgUnit: str  # noqa: N815
    categoryOptionCombo: Optional[str] = None  # noqa: N815
    attributeOptionCombo: Optional[str] = None  # noqa: N815
