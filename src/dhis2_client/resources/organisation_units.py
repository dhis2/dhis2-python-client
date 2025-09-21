from typing import Any, Dict, Iterable, Optional

from .base import Resource


class OrganisationUnits(Resource):
    def list(self, **params) -> Iterable[Dict[str, Any]]:
        return self._list("/api/organisationUnits", params=params, item_key="organisationUnits")

    def get(self, uid: str, *, fields: Optional[str] = None) -> Dict[str, Any]:
        params = {"fields": fields} if fields else None
        return self._get(f"/api/organisationUnits/{uid}", params=params)

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/api/organisationUnits", json=payload)

    def update(self, uid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._put(f"/api/organisationUnits/{uid}", json=payload)

    def delete(self, uid: str) -> Dict[str, Any]:
        return self._delete(f"/api/organisationUnits/{uid}")

    def tree(self, root_uid: Optional[str] = None, levels: Optional[int] = None) -> Dict[str, Any]:
        fields = "id,displayName,level,children[id,displayName,level,children]"
        if root_uid:
            return self._get(f"/api/organisationUnits/{root_uid}", params={"fields": fields})
        return {"organisationUnits": list(self.list(level=1, fields=fields))}

    # GeoJSON (unpaged per DHIS2)
    def geojson(self, **params) -> Dict[str, Any]:
        return self._get("/api/organisationUnits.geojson", params=params)

    def geojson_one(self, uid: str, **params) -> Dict[str, Any]:
        return self._get(f"/api/organisationUnits/{uid}.geojson", params=params)
