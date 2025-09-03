from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .data_element import DataElement
from .data_set import DataSet
from .organisation_unit import OrganisationUnit


class PagedResponse(BaseModel):
    """Common pager container wrapper used by DHIS2 list endpoints."""

    model_config = ConfigDict(extra="ignore")
    pager: Optional[Dict] = None


class OrganisationUnits(PagedResponse):
    organisationUnits: List[OrganisationUnit] = Field(default_factory=list)  # noqa: N815


class DataElements(PagedResponse):
    dataElements: List[DataElement] = Field(default_factory=list)  # noqa: N815


class DataSets(PagedResponse):
    dataSets: List[DataSet] = Field(default_factory=list)  # noqa: N815
