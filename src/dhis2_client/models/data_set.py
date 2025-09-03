from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from .periods import PERIOD_TYPES


class DataSet(BaseModel):
    """DHIS2 DataSet (subset), validating periodType against known DHIS2 period types."""

    model_config = ConfigDict(extra="ignore")
    id: Optional[str] = None
    name: str
    periodType: Optional[str] = None  # noqa: N815

    @field_validator("periodType")
    @classmethod
    def _validate_period_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in PERIOD_TYPES:
            raise ValueError(f"Invalid periodType '{v}'. Must be one of: {sorted(PERIOD_TYPES)}")
        return v
