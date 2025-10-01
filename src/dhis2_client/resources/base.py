from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional

if TYPE_CHECKING:
    from dhis2_client.client import DHIS2Client

class Resource:
    def __init__(self, client: "DHIS2Client") -> None:
        self._c = client

    # convenience pass-throughs
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._c.get(path, params=params)

    def _post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._c.post(path, json=json)

    def _put(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._c.put(path, json=json)

    def _delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._c.delete(path, params=params)

    def _patch(
        self, path: str, *, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return self._c.patch(path, params=params, json=json)

    def _list(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        page_size: Optional[int] = None,
        item_key: Optional[str] = None,
    ) -> Iterable[Dict[str, Any]]:
        return self._c.list_paged(path, params=params, page_size=page_size, item_key=item_key)
