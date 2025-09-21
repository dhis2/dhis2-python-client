# Intentionally empty convenience wrappers may live in client.py for now.
from typing import Any, Dict, Iterable, Optional

from .base import Resource


class DataElements(Resource):
    def list(self, **params) -> Iterable[Dict[str, Any]]:
        return self._list("/api/dataElements", params=params, item_key="dataElements")

    def get(self, uid: str, *, fields: Optional[str] = None) -> Dict[str, Any]:
        params = {"fields": fields} if fields else None
        return self._get(f"/api/dataElements/{uid}", params=params)

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/api/dataElements", json=payload)

    def update(self, uid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._put(f"/api/dataElements/{uid}", json=payload)

    def delete(self, uid: str) -> Dict[str, Any]:
        return self._delete(f"/api/dataElements/{uid}")
