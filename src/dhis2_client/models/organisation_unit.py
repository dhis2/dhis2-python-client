from __future__ import annotations

from typing import Optional

from .common import IdName


class OrganisationUnit(IdName):
    """OrganisationUnit extends IdName and may include a parent link."""

    parent: Optional[IdName] = None
