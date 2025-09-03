from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from .data_value import DataValue


class DataValueSet(BaseModel):
    """Envelope for posting a batch of data values."""

    model_config = ConfigDict(extra="forbid")
    period: str
    dataSet: str  # noqa: N815
    orgUnit: str  # noqa: N815
    dataValues: List[DataValue] = Field(default_factory=list)  # noqa: N815
