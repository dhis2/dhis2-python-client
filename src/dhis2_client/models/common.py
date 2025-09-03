from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class IdName(BaseModel):
    """Minimal DHIS2 entity: (id, name)."""

    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
