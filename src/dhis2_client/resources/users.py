from typing import Any, Dict, Iterable, Optional

from .base import Resource


class Users(Resource):
    def list(self, **params) -> Iterable[Dict[str, Any]]:
        return self._list("/api/users", params=params, item_key="users")

    def get(self, uid: str, *, fields: Optional[str] = None) -> Dict[str, Any]:
        params = {"fields": fields} if fields else None
        return self._get(f"/api/users/{uid}", params=params)
