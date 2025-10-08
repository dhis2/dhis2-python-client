from typing import Any, Dict, Iterable, Optional, List

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

    def geojson(self, **params) -> Dict[str, Any]:
        """
        Raw GeoJSON FeatureCollection of organisation units.
        Mirrors: GET /api/organisationUnits.geojson
        Accepts standard DHIS2 params: fields, filter, level, parent, paging, etc.
        """
        return self._get("/api/organisationUnits.geojson", params=params)

    def geojson_one(self, uid: str, **params) -> Dict[str, Any]:
        """
        Raw GeoJSON for a single organisation unit.
        Mirrors: GET /api/organisationUnits/{uid}.geojson
        """
        return self._get(f"/api/organisationUnits/{uid}.geojson", params=params)

    def geojson_by_level(self, level: int, **params) -> Dict[str, Any]:
        """All OUs at a single absolute level."""
        q = dict(params or {})
        q["level"] = level
        return self.geojson(**q)

    def geojson_children(self, parent_uid: str, **params) -> Dict[str, Any]:
        """
        Immediate children of parent_uid:
        find parent's level, then request level=(parent_level+1) with parent filter.
        """
        parent = self._get(f"/api/organisationUnits/{parent_uid}", params={"fields": "id,level"})
        lvl = parent.get("level")
        if not isinstance(lvl, int):
            raise RuntimeError(f"Could not resolve level for OU {parent_uid}")
        return self.geojson(level=lvl + 1, parent=parent_uid, **params)

    def geojson_subtree(self, root_uid: str, **params) -> Dict[str, Any]:
        """
        Entire subtree under root_uid with **one** .geojson request:
          - read root's absolute level
          - read all orgUnitLevels
          - call /organisationUnits.geojson?parent=<root>&level=L&level=... (for all L >= root_level)

        Mirrors DHIS2 behavior: only OUs that have geometry are returned.
        """
        # 1) root level
        root = self._get(f"/api/organisationUnits/{root_uid}", params={"fields": "id,level"})
        root_level = root.get("level")
        if not isinstance(root_level, int):
            raise RuntimeError(f"Could not resolve level for OU {root_uid}")

        # 2) all levels
        levels_resp = self._get("/api/organisationUnitLevels", params={"paging": "false", "fields": "level,name"})
        all_levels = sorted({item["level"] for item in levels_resp.get("organisationUnitLevels", []) if "level" in item})
        if not all_levels:
            # Fallback: just request with parent (will return direct children at all levels that have geometry)
            return self.geojson(parent=root_uid, **params)

        # 3) select levels >= root level and make ONE call with repeated level params
        wanted_levels = [L for L in all_levels if L >= root_level]
        q = dict(params or {})
        q["level"] = wanted_levels         # httpx expands to &level=...
        q["parent"] = root_uid             # constrain to subtree
        return self.geojson(**q)