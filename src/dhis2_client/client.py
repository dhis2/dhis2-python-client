from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Dict, Iterable, List, Mapping, Optional

import httpx
import structlog

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

DEFAULT_HEADERS: Dict[str, str] = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# -------------------------- NEW tiny helpers --------------------------

def _reveal(value):
    """Return plain string from SecretStr or pass through None/str."""
    if value is None:
        return None
    return value.get_secret_value() if hasattr(value, "get_secret_value") else value

def _get_auth_header_from_settings(settings: Settings) -> Dict[str, str]:
    """
    Support both a property or a method named 'auth_header' on Settings.
    Returns {} if nothing suitable is found.
    """
    # 1) Try attribute-as-property
    try:
        v = settings.auth_header  # property
        if isinstance(v, Mapping):
            return dict(v)
    except Exception:
        pass

    # 2) Try attribute-as-callable
    try:
        maybe_callable = getattr(settings, "auth_header", None)
        if callable(maybe_callable):
            hdr = maybe_callable()
            if isinstance(hdr, Mapping):
                return dict(hdr)
    except Exception:
        pass

    return {}
# ---------------------------------------------------------------------


class DHIS2AsyncClient:
    """Minimal async client for the DHIS2 Web API with paging helpers and typed parsing."""

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
        """
        Build a client from Settings.

        Auth precedence:
          1) If Settings.auth_header (property or method) returns a mapping, use that as headers
          2) Else if username/password present, use Basic auth
          3) Else no auth

        Logging:
          - If Settings has a 'log_level' attribute (e.g., "WARNING", "INFO"), try to configure structlog.
          - If structlog or the attribute isn't available, skip quietly (debug log only).
        """
        # Prefer a ready-made Authorization header from Settings (property or method)
        headers = _get_auth_header_from_settings(settings)

        # Fallback to Basic auth if no header came from Settings
        auth: Optional[httpx.Auth] = None
        if not headers and getattr(settings, "username", None) and getattr(settings, "password", None) is not None:
            pwd = _reveal(settings.password)
            if pwd:
                auth = httpx.BasicAuth(settings.username, pwd)

        # Try optional logging setup from Settings.log_level (if provided)
        try:
            log_level = getattr(settings, "log_level", None)
            if log_level:
                from .logging_conf import configure_logging  # optional dependency
                configure_logging(str(log_level))
        except (ImportError, AttributeError) as e:
            # If structlog isn't available or Settings lacks the field, don't block client creation.
            # Emit a debug-level note via stdlib logging (won't show unless user enables DEBUG).
            import logging as _logging
            _logging.getLogger(__name__).debug("logging_setup_skipped", exc_info=e)

        return cls(
            base_url=str(settings.base_url or ""),
            timeout=float(getattr(settings, "timeout", 30.0)),
            verify_ssl=bool(getattr(settings, "verify_ssl", True)),
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
            raise NetworkError(message=str(te)) from te

    async def _request_json(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Send a request and parse JSON, raising typed errors on HTTP failures (incl. 3xx)."""
        resp = await self._request(method, path, **kwargs)

        # Treat ALL non-2xx as errors (3xx, 4xx, 5xx)
        if not (200 <= resp.status_code < 300):
            # Try to surface server-provided error info
            data = None
            msg = None
            try:
                data = resp.json()
                msg = data.get("message") or data.get("error")
            except Exception:
                # include Location for 3xx to make redirects obvious
                loc = resp.headers.get("Location")
                if loc:
                    msg = f"Redirected to: {loc}"
                else:
                    msg = resp.text or f"HTTP {resp.status_code}"

            raise error_from_status(resp.status_code, msg, path=path, details=data)

        # OK → parse JSON
        try:
            return resp.json()
        except Exception as je:
            raise DHIS2Error(message=f"Invalid JSON: {je}", status_code=resp.status_code, path=path) from None

    # Public HTTP helpers
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

    # ----------------------------- Paging helpers -----------------------------

    async def _list_common(
        self,
        resource: str,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "fields": ",".join(fields),
            "pageSize": page_size,
            "paging": str(paging).lower(),
        }
        if extra_params:
            params.update(extra_params)
        return await self.get(f"/api/{resource}", params=params)

    async def _paginate(
        self,
        resource: str,
        collection_key: str,
        fields: Iterable[str],
        page_size: int = 100,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[List[Dict[str, Any]]]:
        """Yield pages until pager indicates completion; supports pageCount and nextPage styles."""
        current_page = 1
        while True:
            data = await self._list_common(
                resource,
                fields,
                page_size,
                True,
                {**(extra_params or {}), "page": current_page},
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

    async def _list_all(
        self,
        resource: str,
        collection_key: str,
        fields: Iterable[str],
        page_size: int = 100,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Collect all pages into a single list of raw dicts."""
        all_items: List[Dict[str, Any]] = []
        async for page_items in self._paginate(resource, collection_key, fields, page_size, extra_params):
            all_items.extend(page_items)
        return all_items

    # ----------------------------- Typed convenience -----------------------------

    async def get_system_info(self) -> SystemInfo:
        """GET /api/system/info"""
        data = await self.get("/api/system/info")
        return SystemInfo.model_validate(data)

    # OrganisationUnits
    async def get_organisation_units(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
    ) -> List[OrganisationUnit]:
        data = await self._list_common("organisationUnits", fields, page_size, paging=paging)
        return OrganisationUnits.model_validate(data).organisationUnits

    async def iter_organisation_units(
        self,
        fields: Iterable[str],
        page_size: int = 100,
    ) -> AsyncIterator[List[OrganisationUnit]]:
        async for page in self._paginate("organisationUnits", "organisationUnits", fields, page_size):
            yield OrganisationUnits.model_validate({"organisationUnits": page}).organisationUnits

    async def list_all_organisation_units(self, fields: Iterable[str], page_size: int = 100) -> List[OrganisationUnit]:
        raw = await self._list_all("organisationUnits", "organisationUnits", fields, page_size)
        return OrganisationUnits.model_validate({"organisationUnits": raw}).organisationUnits

    # DataElements
    async def get_data_elements(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
    ) -> List[DataElement]:
        data = await self._list_common("dataElements", fields, page_size, paging=paging)
        return DataElements.model_validate(data).dataElements

    async def iter_data_elements(self, fields: Iterable[str], page_size: int = 100) -> AsyncIterator[List[DataElement]]:
        async for page in self._paginate("dataElements", "dataElements", fields, page_size):
            yield DataElements.model_validate({"dataElements": page}).dataElements

    async def list_all_data_elements(self, fields: Iterable[str], page_size: int = 100) -> List[DataElement]:
        raw = await self._list_all("dataElements", "dataElements", fields, page_size)
        return DataElements.model_validate({"dataElements": raw}).dataElements

    # DataSets
    async def get_data_sets(self, fields: Iterable[str], page_size: int = 100, paging: bool = True) -> List[DataSet]:
        data = await self._list_common("dataSets", fields, page_size, paging=paging)
        return DataSets.model_validate(data).dataSets

    async def iter_data_sets(self, fields: Iterable[str], page_size: int = 100) -> AsyncIterator[List[DataSet]]:
        async for page in self._paginate("dataSets", "dataSets", fields, page_size):
            yield DataSets.model_validate({"dataSets": page}).dataSets

    async def list_all_data_sets(self, fields: Iterable[str], page_size: int = 100) -> List[DataSet]:
        raw = await self._list_all("dataSets", "dataSets", fields, page_size)
        return DataSets.model_validate({"dataSets": raw}).dataSets

    # DataValueSets
    async def post_data_value_set(
        self,
        dvs: DataValueSet,
        *,
        import_strategy: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """POST /api/dataValueSets with optional importStrategy and dryRun flags."""
        data = dvs.model_dump() if hasattr(dvs, "model_dump") else dvs
        params: Dict[str, Any] = {}
        if import_strategy:
            params["importStrategy"] = import_strategy
        if dry_run:
            params["dryRun"] = "true"
        return await self._request_json("POST", "/api/dataValueSets", json=data, params=params or None)
