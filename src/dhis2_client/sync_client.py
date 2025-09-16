from __future__ import annotations

import uuid
from typing import Any, Dict, Iterable, List, Optional

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


class DHIS2Client(_ParamsMixin):
    """Synchronous DHIS2 client mirroring the async surface where it fits."""

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
        self._client: Optional[httpx.Client] = None

    def __enter__(self) -> DHIS2Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self._base_url,
                timeout=self._timeout,
                verify=self._verify_ssl,
                headers=self._headers,
                auth=self._auth,
            )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    @classmethod
    def from_settings(cls, settings: Settings) -> DHIS2Client:
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

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("Use 'with DHIS2Client(...)'")
        request_id = str(uuid.uuid4())
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("X-Request-ID", request_id)
        kwargs["headers"] = headers
        try:
            logger.info("http.request", method=method, path=path, request_id=request_id)
            resp = self._client.request(method, path, **kwargs)
            logger.info("http.response", status=resp.status_code, path=path, request_id=request_id)
            return resp
        except httpx.TransportError as te:
            logger.error("http.network_error", error=str(te), path=path, request_id=request_id)
            raise NetworkError(message=str(te)) from None

    def _request_json(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        resp = self._request(method, path, **kwargs)
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

    def get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request_json("GET", path, params=params)

    def post_json(self, path: str, payload: Any) -> Dict[str, Any]:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload
        return self._request_json("POST", path, json=data)

    def put_json(self, path: str, payload: Any) -> Dict[str, Any]:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload
        return self._request_json("PUT", path, json=data)

    def delete(self, path: str) -> Dict[str, Any]:
        return self._request_json("DELETE", path)

    # ----------------------------- Paging & typed -----------------------------

    def _list_common(
        self,
        resource: str,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        params = self._mk_params(fields, page_size, paging, extra_params)
        return self.get(f"/api/{resource}", params=params)

    def _paginate(
        self,
        resource: str,
        collection_key: str,
        fields: Iterable[str],
        page_size: int = 100,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[List[Dict[str, Any]]]:
        pages: List[List[Dict[str, Any]]] = []
        current_page = 1
        while True:
            data = self._list_common(resource, fields, page_size, True, {**(extra_params or {}), "page": current_page})
            items = data.get(collection_key, []) or []
            pages.append(items)
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
        return pages

    def _list_all(
        self,
        resource: str,
        collection_key: str,
        fields: Iterable[str],
        page_size: int = 100,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        all_items: List[Dict[str, Any]] = []
        for page in self._paginate(resource, collection_key, fields, page_size, extra_params):
            all_items.extend(page)
        return all_items

    # ---- typed ----

    def get_system_info(self, *, as_dict: bool = False):
        data = self.get("/api/system/info")
        if as_dict:
            return data
        return SystemInfo.model_validate(data)

    def get_organisation_units(
        self,
        fields: Iterable[str],
        page_size: int = 100,
        paging: bool = True,
        *,
        as_dict: bool = False,
    ):
        data = self._list_common("organisationUnits", fields, page_size, paging=paging)
        if as_dict:
            return data.get("organisationUnits", [])
        return OrganisationUnits.model_validate(data).organisationUnits

    def list_all_organisation_units(
        self, fields: Iterable[str], page_size: int = 100, *, as_dict: bool = False
    ) -> List[OrganisationUnit]:
        raw = self._list_all("organisationUnits", "organisationUnits", fields, page_size)
        if as_dict:
            return raw
        return OrganisationUnits.model_validate({"organisationUnits": raw}).organisationUnits

    def get_data_elements(
        self, fields: Iterable[str], page_size: int = 100, paging: bool = True, *, as_dict: bool = False
    ) -> List[DataElement]:
        data = self._list_common("dataElements", fields, page_size, paging=paging)
        if as_dict:
            return data.get("dataElements", [])
        return DataElements.model_validate(data).dataElements

    def list_all_data_elements(
        self, fields: Iterable[str], page_size: int = 100, *, as_dict: bool = False
    ) -> List[DataElement]:
        raw = self._list_all("dataElements", "dataElements", fields, page_size)
        if as_dict:
            return raw
        return DataElements.model_validate({"dataElements": raw}).dataElements

    def get_data_sets(
        self, fields: Iterable[str], page_size: int = 100, paging: bool = True, *, as_dict: bool = False
    ) -> List[DataSet]:
        data = self._list_common("dataSets", fields, page_size, paging=paging)
        if as_dict:
            return data.get("dataSets", [])
        return DataSets.model_validate(data).dataSets

    def list_all_data_sets(
        self, fields: Iterable[str], page_size: int = 100, *, as_dict: bool = False
    ) -> List[DataSet]:
        raw = self._list_all("dataSets", "dataSets", fields, page_size)
        if as_dict:
            return raw
        return DataSets.model_validate({"dataSets": raw}).dataSets

    def post_data_value_set(
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
        return self._request_json("POST", "/api/dataValueSets", json=data, params=params or None)
