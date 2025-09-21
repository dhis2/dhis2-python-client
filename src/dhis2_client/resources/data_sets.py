# Intentionally empty convenience wrappers may live in client.py for now.
from typing import Any, Dict, Iterable, Optional

from .base import Resource


class DataSets(Resource):
    def list(self, **params) -> Iterable[Dict[str, Any]]:
        return self._list("/api/dataSets", params=params, item_key="dataSets")

    def get(self, uid: str, *, fields: Optional[str] = None) -> Dict[str, Any]:
        params = {"fields": fields} if fields else None
        return self._get(f"/api/dataSets/{uid}", params=params)

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/api/dataSets", json=payload)

    def update(self, uid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._put(f"/api/dataSets/{uid}", json=payload)

    def delete(self, uid: str) -> Dict[str, Any]:
        return self._delete(f"/api/dataSets/{uid}")
