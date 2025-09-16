from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Union

import httpx
import structlog

from ._base import DEFAULT_HEADERS, _get_auth_header_from_settings, _ParamsMixin, _reveal
from .exceptions import DHIS2Error, NetworkError, error_from_status
from .models import (
    DataElement,
    DataElements,
    DataSet,
    DataSets,
    DataValueSet,
    OrganisationUnit,
    OrganisationUnits,
    SystemInfo,
)
from .settings import Settings

logger = structlog.get_logger("dhis2_client")

# ----------------------------- JSON type aliases -----------------------------
JSONScalar = Union[str, int, float, bool, None]
JSONObj = Dict[str, "JSON"]
JSONArray = List["JSON"]
JSON = Union[JSONScalar, JSONObj, JSONArray]


class DHIS2AsyncClient(_ParamsMixin):
    """Async DHIS2 client.

    Default return behavior is controlled by Settings.return_models:
      - return_models = False  → default is dict/JSON
      - return_models = True   → default is Pydantic models

    Each typed method accepts `as_dict: Optional[bool] = None` to override per call:
      - as_dict=True  → force dict/JSON
      - as_dict=False → force Pydantic models
      - as_dict=None  → use Settings.return_models default
    """

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[httpx.Auth] = None,
        return_models: bool = False,  # global default if not using from_settings
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._headers = dict(DEFAULT_HEADERS)
        if headers:
            self._headers.update(headers)
        self._auth = auth
        self._client: Optional[httpx.AsyncClient] = None
        self._return_models = bool(return_models)

    async def __aenter__(self) -> DHIS2AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                verify=self._verify_ssl,
                headers=self._headers,
                auth=self._auth,
            )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @classmethod
    def from_settings(cls, settings: Settings) -> DHIS2AsyncClient:
        # best-effort logging setup (don’t block)
        try:
            from .logging_conf import configure_logging

            configure_logging(getattr(settings, "log_level", None))
        except (ImportError, AttributeError):
            import logging as _logging

            _logging.getLogger(__name__).debug("logging_setup_skipped", exc_info=True)

        headers = _get_auth_header_from_settings(settings)
        auth: Optional[httpx.Auth] = None
        if not headers and settings.username and getattr(settings, "password", None) is not None:
            pwd = _reveal(settings.password)
            if pwd:
                auth = httpx.BasicAuth(settings.username, pwd)
        return cls(
            base_url=str(settings.base_url or ""),
            timeout=float(settings.timeout),
            verify_ssl=bool(settings.verify_ssl),
            headers=headers or None,
            auth=auth,
            return_models=bool(getattr(settings, "return_models", False)),
        )

    # ----------------------------- HTTP core -----------------------------

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("Use 'async with DHIS2AsyncClient(...)'")
        request_id = str(uuid.uuid4())
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("X-Request-ID", request_id)
        kwargs["headers"] = headers
        try:
            logger.info("http.request", method=method, path=path, request_id=request_id)
            resp = await self._client.request(method, path, **kwargs)
            logger.info("http.response", status=resp.status_code, path=path, request_id=request_id)
            return resp
        except httpx.TransportError as te:
            logger.error("http.network_error", error=str(te), path=path, request_id=request_id)
            raise NetworkError(message=str(te)) from None

    async def _request_json(self, method: str, path: str, **kwargs) -> JSONObj:
        resp = await self._request(method, path, **kwargs)
        if not (200 <= resp.status_code < 300):
            data: Optional[JSON] = None
            msg: Optional[str] = None
            try:
                data = resp.json()
                if isinstance(data, dict):
                    msg = data.get("message") or data.get("error")  # type: ignore[union-attr]
            except Exception:
                loc = resp.headers.get("Location")
                msg = f"Redirected to: {loc}" if loc else resp.text or f"HTTP {resp.status_code}"
            raise error_from_status(resp.status_code, msg, path=path, details=data)
        try:
            parsed = resp.json()
            if not isinstance(parsed, dict):
                raise TypeError(f"Expected JSON object, got {type(parsed).__name__}")
            return parsed
        except Exception as je:
            raise DHIS2Error(message=f"Invalid JSON: {je}", status_code=resp.status_code, path=path) from None

    # ----------------------------- Raw helpers -----------------------------

    async def get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> JSONObj:
        """GET path and return parsed JSON object."""
        return await self._request_json("GET", path, params=params)

    async def post_json(self, path: str, payload: Any) -> JSONObj:
        """POST JSON-serializable payload (pydantic models supported)."""
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload
        return await self._request_json("POST", path, json=data)

    async def put_json(self, path: str, payload: Any) -> JSONObj:
        """PUT JSON-serializable payload (pydantic models supported)."""
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload
        return await self._request_json("PUT", path, json=data)

    async def delete(self, path: str) -> JSONObj:
        """DELETE and return parsed JSON object (if any)."""
        return await self._request_json("DELETE", path)

    # ----------------------------- Paging & typed -----------------------------

    async def _list_common(
        self,
        resource: str,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> JSONObj:
        params = self._mk_params(fields, page_size, paging, extra_params)
        return await self.get(f"/api/{resource}", params=params)

    async def _paginate(
        self,
        resource: str,
        collection_key: str,
        fields: Iterable[str],
        page_size: int = 100,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[List[JSONObj]]:
        current_page = 1
        while True:
            data = await self._list_common(
                resource, fields, page_size, True, {**(extra_params or {}), "page": current_page}
            )
            items = data.get(collection_key, []) or []
            if not isinstance(items, list):
                raise DHIS2Error(message=f"Expected list at key '{collection_key}'", path=f"/api/{resource}")
            yield [i for i in items if isinstance(i, dict)]
            pager = data.get("pager") or {}
            page = pager.get("page") if isinstance(pager, dict) else None
            page_count = pager.get("pageCount") if isinstance(pager, dict) else None
            next_page_url = (pager.get("nextPage") if isinstance(pager, dict) else None) or data.get("nextPage")
            if page_count and page:
                if page >= page_count:
                    break
                current_page += 1
            elif next_page_url:
                current_page += 1
            else:
                break

    # ---- default-resolution helper ----

    def _resolve_as_dict(self, as_dict: Optional[bool]) -> bool:
        return as_dict if as_dict is not None else (not self._return_models)

    # ---- typed (default from settings) ----

    async def get_system_info(self, *, as_dict: Optional[bool] = None) -> JSONObj | SystemInfo:
        data = await self.get("/api/system/info")
        return data if self._resolve_as_dict(as_dict) else SystemInfo.model_validate(data)

    async def get_organisation_units(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
        *,
        as_dict: Optional[bool] = None,
    ) -> List[JSONObj] | List[OrganisationUnit]:
        data = await self._list_common("organisationUnits", fields, page_size, paging=paging)
        if self._resolve_as_dict(as_dict):
            items = data.get("organisationUnits", []) or []
            return [i for i in items if isinstance(i, dict)]
        return OrganisationUnits.model_validate(data).organisationUnits

    async def iter_organisation_units(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        *,
        as_dict: Optional[bool] = None,
    ) -> AsyncIterator[List[JSONObj] | List[OrganisationUnit]]:
        async for page in self._paginate("organisationUnits", "organisationUnits", fields, page_size):
            if self._resolve_as_dict(as_dict):
                yield page
            else:
                yield OrganisationUnits.model_validate({"organisationUnits": page}).organisationUnits

    async def list_all_organisation_units(
        self, fields: Iterable[str], page_size: int = 100, *, as_dict: Optional[bool] = None
    ) -> List[JSONObj] | List[OrganisationUnit]:
        if self._resolve_as_dict(as_dict):
            out: List[JSONObj] = []
            async for chunk in self.iter_organisation_units(fields, page_size, as_dict=True):
                out.extend(chunk)  # type: ignore[arg-type]
            return out
        out_m: List[OrganisationUnit] = []
        async for chunk in self.iter_organisation_units(fields, page_size, as_dict=False):
            out_m.extend(chunk)
        return OrganisationUnits.model_validate({"organisationUnits": out_m}).organisationUnits

    async def get_data_elements(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
        *,
        as_dict: Optional[bool] = None,
    ) -> List[JSONObj] | List[DataElement]:
        data = await self._list_common("dataElements", fields, page_size, paging=paging)
        if self._resolve_as_dict(as_dict):
            items = data.get("dataElements", []) or []
            return [i for i in items if isinstance(i, dict)]
        return DataElements.model_validate(data).dataElements

    async def iter_data_elements(
        self, fields: Iterable[str], page_size: int = 100, *, as_dict: Optional[bool] = None
    ) -> AsyncIterator[List[JSONObj] | List[DataElement]]:
        async for page in self._paginate("dataElements", "dataElements", fields, page_size):
            if self._resolve_as_dict(as_dict):
                yield page
            else:
                yield DataElements.model_validate({"dataElements": page}).dataElements

    async def list_all_data_elements(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        *,
        as_dict: Optional[bool] = None,
    ) -> List[JSONObj] | List[DataElement]:
        if self._resolve_as_dict(as_dict):
            out: List[JSONObj] = []
            async for chunk in self.iter_data_elements(fields, page_size, as_dict=True):
                out.extend(chunk)  # type: ignore[arg-type]
            return out
        out_m: List[DataElement] = []
        async for chunk in self.iter_data_elements(fields, page_size, as_dict=False):
            out_m.extend(chunk)
        return DataElements.model_validate({"dataElements": out_m}).dataElements

    async def get_data_sets(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
        *,
        as_dict: Optional[bool] = None,
    ) -> List[JSONObj] | List[DataSet]:
        data = await self._list_common("dataSets", fields, page_size, paging=paging)
        if self._resolve_as_dict(as_dict):
            items = data.get("dataSets", []) or []
            return [i for i in items if isinstance(i, dict)]
        return DataSets.model_validate(data).dataSets

    async def iter_data_sets(
        self, fields: Iterable[str], page_size: int = 100, *, as_dict: Optional[bool] = None
    ) -> AsyncIterator[List[JSONObj] | List[DataSet]]:
        async for page in self._paginate("dataSets", "dataSets", fields, page_size):
            if self._resolve_as_dict(as_dict):
                yield page
            else:
                yield DataSets.model_validate({"dataSets": page}).dataSets

    async def list_all_data_sets(
        self, fields: Iterable[str], page_size: int = 100, *, as_dict: Optional[bool] = None
    ) -> List[JSONObj] | List[DataSet]:
        if self._resolve_as_dict(as_dict):
            out: List[JSONObj] = []
            async for chunk in self.iter_data_sets(fields, page_size, as_dict=True):
                out.extend(chunk)  # type: ignore[arg-type]
            return out
        out_m: List[DataSet] = []
        async for chunk in self.iter_data_sets(fields, page_size, as_dict=False):
            out_m.extend(chunk)
        return DataSets.model_validate({"dataSets": out_m}).dataSets

    async def post_data_value_set(
        self,
        dvs: DataValueSet,
        *,
        import_strategy: Optional[str] = None,
        dry_run: bool = False,
    ) -> JSONObj:
        data = dvs.model_dump() if hasattr(dvs, "model_dump") else dvs
        params: Dict[str, Any] = {}
        if import_strategy:
            params["importStrategy"] = import_strategy
        if dry_run:
            params["dryRun"] = "true"
        return await self._request_json("POST", "/api/dataValueSets", json=data, params=params or None)
