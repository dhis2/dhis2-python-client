# Intentionally empty convenience wrappers may live in client.py for now.
from typing import Any, Dict

from .base import Resource


class Analytics(Resource):
    def get(self, *, table: str = "analytics", **params) -> Dict[str, Any]:
        return self._get(f"/api/{table}", params=params)
