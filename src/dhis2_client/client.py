from typing import Any, Dict, Iterable, Optional

import atexit
import httpx

from .errors import DHIS2HTTPError
from .logging import configure_logging, logger
from .paging import infer_item_key
from .resources import (
    Analytics,
    DataElements,
    DataSets,
    DataValues,
    OrganisationUnits,
    Users,
    Sharing,
)
from .resources.system import System
from .settings import ClientSettings
from .utils.utils import build_url


class DHIS2Client:
    """
    Thin, synchronous DHIS2 Web API client.

    - Dict/JSON in & out (no Pydantic).
    - Stdlib logging (default JSON output when configured).
    - Basic auth by default, token optional.
    - Clean paging via list_paged() and fetch_all().
    - Convenience methods delegate to resource classes.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        default_page_size: int = 50,
        timeout: float = 30.0,
        retries: int = 3,
        verify_ssl: bool = True,
        settings: ClientSettings | None = None,
        log_level: str | None = None,
        log_format: str | None = None,  # "json" (default) or "text"
        log_destination: str | None = None,
    ) -> None:
        # Apply settings if provided
        if settings:
            configure_logging(
                level=log_level or settings.log_level,
                fmt=(log_format or settings.log_format),
                destination=(log_destination or settings.log_destination),
            )
            base_url = base_url or settings.base_url
            username = username or settings.username
            password = password or settings.password
            token = token or settings.token
            default_page_size = (
                default_page_size if default_page_size != 50 else settings.default_page_size
            )
            timeout = timeout if timeout != 30.0 else settings.timeout
            retries = retries if retries != 3 else settings.retries
            verify_ssl = verify_ssl if verify_ssl is not True else settings.verify_ssl
            self.model_mode = settings.model_mode
        else:
            if log_level or log_format or log_destination:
                configure_logging(
                    level=log_level or "WARNING",
                    fmt=(log_format or "json"),
                    destination=log_destination,
                )
            self.model_mode = "raw"

        if not base_url:
            raise ValueError("base_url is required")

        self.base_url = base_url.rstrip("/")
        self.default_page_size = int(default_page_size)
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.verify_ssl = bool(verify_ssl)

        # Persist auth + token
        self._auth = (username, password) if (username and password) else None
        if token:
            self._token_header = (
                token if token.startswith(("Bearer ", "ApiToken ")) else f"ApiToken {token}"
            )
        else:
            self._token_header = None

        # Build initial client (auto-open)
        self._client: Optional[httpx.Client] = self._build_client()

        # Best-effort cleanup at interpreter exit; safe to call multiple times.
        atexit.register(self.close)

        # Register resources
        self._system = System(self)
        self._users = Users(self)
        self._org_units = OrganisationUnits(self)
        self._data_elements = DataElements(self)
        self._data_sets = DataSets(self)
        self._data_values = DataValues(self)
        self._analytics = Analytics(self)
        self._sharing = Sharing(self)

    # ---------- lifecycle ----------

    def _build_client(self) -> httpx.Client:
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._token_header:
            headers["Authorization"] = self._token_header
        return httpx.Client(
            headers=headers,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

    def _ensure_client(self) -> httpx.Client:
        """
        Recreate the httpx.Client if it was closed.
        This makes client.close() safe mid-process (e.g., notebooks).
        """
        if self._client is None:
            logger.debug("Recreating HTTP client")
            self._client = self._build_client()
        return self._client

    def close(self) -> None:
        """Idempotent close of the underlying HTTP client."""
        client, self._client = self._client, None
        if client is not None:
            try:
                client.close()
            except Exception as e:
                logger.warning("Error during client.close(): %s", e)

    # -------------------------
    # Core HTTP (pass-throughs)
    # -------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = build_url(self.base_url, path)
        logger.info("Request %s %s params=%s", method, path, params)

        resp: httpx.Response | None = None
        for attempt in range(self.retries + 1):
            client = self._ensure_client()
            resp = client.request(method, url, params=params, json=json, auth=self._auth, headers=headers)
            if resp.status_code >= 500 and method.upper() == "GET" and attempt < self.retries:
                logger.warning(
                    "Retrying %s %s after server error %s (attempt %s)",
                    method,
                    path,
                    resp.status_code,
                    attempt + 1,
                )
                continue
            break

        assert resp is not None
        if resp.status_code // 100 != 2:
            try:
                payload = resp.json()
            except Exception:
                payload = {"message": resp.text}
            logger.error("HTTP %s on %s: %s", resp.status_code, path, payload)
            raise DHIS2HTTPError(resp.status_code, path, payload)

        data: Dict[str, Any] = resp.json() if resp.content else {}
        if isinstance(data, dict) and data.get("pager"):
            p = data["pager"]
            logger.info(
                "Pager: page=%s/%s total=%s", p.get("page"), p.get("pageCount"), p.get("total")
            )
        return data

    def get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", path, params=params)

    def post(
        self, path: str, *, params: Dict[str, Any] | None = None, json: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return self._request("POST", path, params=params, json=json)

    def put(
        self, path: str, *, params: Dict[str, Any] | None = None, json: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return self._request("PUT", path, params=params, json=json)

    def patch(
        self, path: str, *, params: dict | None = None, json: dict | list | None = None
    ) -> dict:
        return self._request(
            "PATCH",
            path,
            params=params,
            json=json,
            headers={"Content-Type": "application/json-patch+json"},
        )

    def delete(self, path: str, *, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return self._request("DELETE", path, params=params)

    # -------------------------
    # Paging helpers
    # -------------------------

    def list_paged(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        page_size: Optional[int] = None,
        item_key: Optional[str] = None,
    ) -> Iterable[Dict[str, Any]]:
        page = 1
        page_size = page_size or self.default_page_size
        params = dict(params or {})
        params.setdefault("pageSize", page_size)
        params.setdefault("page", page)

        while True:
            data = self.get(path, params=params)
            key = item_key or infer_item_key(data)
            items = data.get(key, []) if isinstance(data, dict) else []
            for it in items:
                yield it

            pager = data.get("pager") if isinstance(data, dict) else None
            if not pager or pager.get("page") >= pager.get("pageCount"):
                break
            params["page"] = pager.get("page", page) + 1

    def fetch_all(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        item_key: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        return list(self.list_paged(path, params=params, item_key=item_key, page_size=page_size))

    # --------------------------------
    # Public convenience (delegations)
    # --------------------------------

    # System
    def get_system_info(self) -> Dict[str, Any]:
        return self._system.info()

    # Users (read-only + OU scope updater)
    def get_current_user(self, *, fields: str | None = None) -> dict:
        params = {"fields": fields} if fields else None
        return self.get("/api/me", params=params)

    def get_users(self, **params):
        return self._users.list(**params)

    def get_user(self, uid: str, *, fields: str | None = None) -> Dict[str, Any]:
        return self._users.get(uid, fields=fields)

    def add_user_org_unit_scopes(self, uid: str, **kwargs) -> dict:
        return self._users.add_user_org_unit_scopes(uid, **kwargs)

    def replace_user_org_unit_scopes(self, uid: str, **kwargs) -> dict:
        return self._users.replace_user_org_unit_scopes(uid, **kwargs)

    def remove_user_org_unit_scopes(self, uid: str, **kwargs) -> dict:
        return self._users.remove_user_org_unit_scopes(uid, **kwargs)

    def add_my_org_unit_scopes(self, **kwargs) -> dict:
        return self._users.add_my_org_unit_scopes(**kwargs)

    def replace_my_org_unit_scopes(self, **kwargs) -> dict:
        return self._users.replace_my_org_unit_scopes(**kwargs)

    def remove_my_org_unit_scopes(self, **kwargs) -> dict:
        return self._users.remove_my_org_unit_scopes(**kwargs)

    # Organisation Units
    def get_organisation_units(self, **params):
        return self._org_units.list(**params)

    def get_org_unit(self, uid: str, *, fields: str | None = None) -> Dict[str, Any]:
        return self._org_units.get(uid, fields=fields)

    def create_org_unit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._org_units.create(payload)

    def update_org_unit(self, uid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._org_units.update(uid, payload)

    def delete_org_unit(self, uid: str) -> Dict[str, Any]:
        return self._org_units.delete(uid)

    def get_org_unit_tree(
        self, root_uid: str | None = None, levels: int | None = None
    ) -> Dict[str, Any]:
        return self._org_units.tree(root_uid=root_uid, levels=levels)

    # GeoJSON
    def get_org_units_geojson(self, **params) -> dict:
        return self._org_units.geojson(**params)

    def get_org_unit_geojson(self, uid: str, **params) -> dict:
        return self._org_units.geojson_one(uid, **params)

    def get_org_units_geojson_by_level(self, level: int, **params) -> dict:
        return self._org_units.geojson_by_level(level, **params)

    def get_org_unit_children_geojson(self, parent_uid: str, **params) -> dict:
        return self._org_units.geojson_children(parent_uid, **params)

    def get_org_unit_subtree_geojson(self, root_uid: str, **params) -> dict:
        return self._org_units.geojson_subtree(root_uid, **params)

    # Data Elements
    def get_data_elements(self, **params):
        return self._data_elements.list(**params)

    def get_data_element(self, uid: str, *, fields: str | None = None) -> Dict[str, Any]:
        return self._data_elements.get(uid, fields=fields)

    def create_data_element(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._data_elements.create(payload)

    def update_data_element(self, uid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._data_elements.update(uid, payload)

    def delete_data_element(self, uid: str) -> Dict[str, Any]:
        return self._data_elements.delete(uid)

    # Data Sets
    def get_data_sets(self, **params):
        return self._data_sets.list(**params)

    def get_data_set(self, uid: str, *, fields: str | None = None) -> Dict[str, Any]:
        return self._data_sets.get(uid, fields=fields)

    def create_data_set(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._data_sets.create(payload)

    def update_data_set(self, uid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._data_sets.update(uid, payload)

    def delete_data_set(self, uid: str) -> Dict[str, Any]:
        return self._data_sets.delete(uid)

    # Data Values
    def get_data_value(self, de: str, pe: str, ou: str, **kwargs) -> Dict[str, Any]:
        return self._data_values.get(de, pe, ou, **kwargs)

    def set_data_value(
        self, de: str, pe: str, ou: str, value: str | int | float, *, co: str, ao: str | None = None
    ) -> Dict[str, Any]:
        return self._data_values.set(de, pe, ou, value, co=co, ao=ao)

    def delete_data_value(self, de: str, pe: str, ou: str, *, co: str) -> Dict[str, Any]:
        return self._data_values.delete(de, pe, ou, co=co)

    def get_data_value_set(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._data_values.get_set(params)

    def post_data_value_set(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._data_values.post_set(payload)

    # Analytics
    def get_analytics(self, *, table: str = "analytics", **params) -> Dict[str, Any]:
        return self._analytics.get(table=table, **params)

    def analytics_latest_period_for_level(self, de_uid: str, level: int) -> Dict[str, Any]:
        return self._analytics.latest_period_for_level(de_uid, level)

    # Sharing
    def get_sharing(self, *, object_type: str, object_id: str) -> dict:
        return self._sharing.get(object_type=object_type, object_id=object_id)

    def set_sharing(self, *, object_type: str, object_id: str, **kwargs) -> dict:
        return self._sharing.set(object_type=object_type, object_id=object_id, **kwargs)

    def grant_self_access(self, *, object_type: str, object_id: str, access: str = "r-rw----") -> dict:
        return self._sharing.grant_self_access(object_type=object_type, object_id=object_id, access=access)

    def set_public_access(self, *, object_type: str, object_id: str, public_access: str) -> dict:
        return self._sharing.set_public_access(object_type=object_type, object_id=object_id, public_access=public_access)

    def grant_access(
        self,
        *,
        object_type: str,
        object_id: str,
        user_ids: Optional[Iterable[str]] = None,
        user_group_ids: Optional[Iterable[str]] = None,
        access: str = "r-rw----",
        keep_public: bool = True,
    ) -> dict:
        return self._sharing.grant_access(
            object_type=object_type,
            object_id=object_id,
            user_ids=user_ids,
            user_group_ids=user_group_ids,
            access=access,
            keep_public=keep_public,
        )

    def grant_self_data_write_on_dataset(self, dataset_id: str, access: str = "rwrw----") -> dict:
        return self._sharing.grant_self_data_write_on_dataset(dataset_id, access=access)

    def set_dataset_data_write(self, dataset_id: str, **kwargs) -> dict:
        return self._sharing.set_dataset_data_write(dataset_id, **kwargs)