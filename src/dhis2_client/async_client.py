from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional

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


class DHIS2AsyncClient(_ParamsMixin):
    """Async DHIS2 client with paging helpers and typed parsing."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[httpx.Auth] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._headers = dict(DEFAULT_HEADERS)
        if headers:
            self._headers.update(headers)
        self._auth = auth
        self._client: Optional[httpx.AsyncClient] = None

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
        except Exception:  # noqa: BLE001
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

    async def _request_json(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        resp = await self._request(method, path, **kwargs)
        if not (200 <= resp.status_code < 300):
            data = None
            msg = None
            try:
                data = resp.json()
                msg = data.get("message") or data.get("error")
            except Exception:
                loc = resp.headers.get("Location")
                msg = f"Redirected to: {loc}" if loc else resp.text or f"HTTP {resp.status_code}"
            raise error_from_status(resp.status_code, msg, path=path, details=data)
        try:
            return resp.json()
        except Exception as je:
            raise DHIS2Error(message=f"Invalid JSON: {je}", status_code=resp.status_code, path=path) from None

    # ----------------------------- Raw helpers -----------------------------

    async def get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET path and return parsed JSON dict."""
        return await self._request_json("GET", path, params=params)

    async def post_json(self, path: str, payload: Any) -> Dict[str, Any]:
        """POST JSON-serializable payload (pydantic models supported)."""
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload
        return await self._request_json("POST", path, json=data)

    async def put_json(self, path: str, payload: Any) -> Dict[str, Any]:
        """PUT JSON-serializable payload (pydantic models supported)."""
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload
        return await self._request_json("PUT", path, json=data)

    async def delete(self, path: str) -> Dict[str, Any]:
        """DELETE and return parsed JSON dict (if any)."""
        return await self._request_json("DELETE", path)

    # ----------------------------- Paging & typed -----------------------------

    async def _list_common(
        self,
        resource: str,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        params = self._mk_params(fields, page_size, paging, extra_params)
        return await self.get(f"/api/{resource}", params=params)

    async def _paginate(
        self,
        resource: str,
        collection_key: str,
        fields: Iterable[str],
        page_size: int = 100,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[List[Dict[str, Any]]]:
        current_page = 1
        while True:
            data = await self._list_common(
                resource, fields, page_size, True, {**(extra_params or {}), "page": current_page}
            )
            items = data.get(collection_key, []) or []
            yield items
            pager = data.get("pager") or {}
            page = pager.get("page")
            page_count = pager.get("pageCount")
            next_page_url = pager.get("nextPage") or data.get("nextPage")
            if page_count and page:
                if page >= page_count:
                    break
                current_page += 1
            elif next_page_url:
                current_page += 1
            else:
                break

    async def get_system_info(self, *, as_dict: bool = False):
        data = await self.get("/api/system/info")
        if as_dict:
            return data
        return SystemInfo.model_validate(data)

    async def get_organisation_units(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
        *,
        as_dict: bool = False,
    ):
        data = await self._list_common("organisationUnits", fields, page_size, paging=paging)
        if as_dict:
            return data.get("organisationUnits", [])
        return OrganisationUnits.model_validate(data).organisationUnits

    async def iter_organisation_units(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        *,
        as_dict: bool = False,
    ) -> AsyncIterator[List[Any]]:
        async for page in self._paginate("organisationUnits", "organisationUnits", fields, page_size):
            if as_dict:
                yield page
            else:
                yield OrganisationUnits.model_validate({"organisationUnits": page}).organisationUnits


    async def list_all_organisation_units(self, fields: Iterable[str], page_size: int = 100, *, as_dict: bool = False):
        if as_dict:
            out: List[Dict[str, Any]] = []
            async for chunk in self.iter_organisation_units(fields, page_size):
                out.extend(chunk)
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
        as_dict: bool = False,
    ):
        data = await self._list_common("dataElements", fields, page_size, paging=paging)
        if as_dict:
            return data.get("dataElements", []) or []
        return DataElements.model_validate(data).dataElements

    async def iter_data_elements(
        self, fields: Iterable[str], page_size: int = 100, *, as_dict: bool = False
    ) -> AsyncIterator[List[Any]]:
        async for page in self._paginate("dataElements", "dataElements", fields, page_size):
            if as_dict:
                yield page
            else:
                yield DataElements.model_validate({"dataElements": page}).dataElements

    async def list_all_data_elements(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        *,
        as_dict: bool = False,
    ):
        if as_dict:
            out: List[Dict[str, Any]] = []
            async for chunk in self.iter_data_elements(fields, page_size):
                out.extend(chunk)
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
        as_dict: bool = False,
    ):
        data = await self._list_common("dataSets", fields, page_size, paging=paging)
        if as_dict:
            return data.get("dataSets", []) or []
        return DataSets.model_validate(data).dataSets

    async def iter_data_sets(
        self, fields: Iterable[str], page_size: int = 100, *, as_dict: bool = False
    ) -> AsyncIterator[List[Any]]:
        async for page in self._paginate("dataSets", "dataSets", fields, page_size):
            if as_dict:
                yield page
            else:
                yield DataSets.model_validate({"dataSets": page}).dataSets

    async def list_all_data_sets(self, fields: Iterable[str], page_size: int = 100, *, as_dict: bool = False):
        if as_dict:
            out: List[Dict[str, Any]] = []
            async for chunk in self._paginate(
                "dataSets",
                "dataSets",
                fields,
                page_size,
            ):
                out.extend(chunk)
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
    ) -> Dict[str, Any]:
        data = dvs.model_dump() if hasattr(dvs, "model_dump") else dvs
        params: Dict[str, Any] = {}
        if import_strategy:
            params["importStrategy"] = import_strategy
        if dry_run:
            params["dryRun"] = "true"
        return await self._request_json("POST", "/api/dataValueSets", json=data, params=params or None)
