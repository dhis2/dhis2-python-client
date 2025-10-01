from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, List

from .base import Resource


class Users(Resource):
    """
    Users resource with safe JSON Patch helpers for OrgUnit scopes.
    Scopes:
      - capture → /organisationUnits
      - view    → /dataViewOrganisationUnits
      - tei     → /teiSearchOrganisationUnits
    """

    # -------- basic reads (unchanged style) -------- #

    def list(self, **params) -> Iterable[Dict[str, Any]]:
        return self._list("/api/users", params=params, item_key="users")

    def get(self, uid: str, *, fields: Optional[str] = None) -> Dict[str, Any]:
        params = {"fields": fields} if fields else None
        return self._get(f"/api/users/{uid}", params=params)

    # ------------- internals ------------- #

    @staticmethod
    def _ids_to_objs(ids: Iterable[str]) -> List[Dict[str, str]]:
        return [{"id": i} for i in ids]

    @staticmethod
    def _to_id_set(items: Optional[Iterable[Dict[str, str]]]) -> set[str]:
        return {x["id"] for x in (items or [])}

    @staticmethod
    def _paths() -> Dict[str, str]:
        # scope -> json pointer path
        return {
            "capture": "/organisationUnits",
            "view": "/dataViewOrganisationUnits",
            "tei": "/teiSearchOrganisationUnits",
        }

    # ------------- JSON Patch helpers ------------- #

    def add_user_org_unit_scopes(
        self,
        uid: str,
        *,
        capture: Optional[Iterable[str]] = None,
        view: Optional[Iterable[str]] = None,
        tei: Optional[Iterable[str]] = None,
        dedupe: bool = True,
    ) -> Dict[str, Any]:
        """
        Append OUs to the user's scopes (does not touch other fields).
        When dedupe=True, we first read current arrays and skip already-present IDs.
        """
        ops: List[Dict[str, Any]] = []
        paths = self._paths()

        if dedupe:
            cur = self.get(
                uid,
                fields="organisationUnits[id],dataViewOrganisationUnits[id],teiSearchOrganisationUnits[id]",
            )
            have_cap = self._to_id_set(cur.get("organisationUnits"))
            have_view = self._to_id_set(cur.get("dataViewOrganisationUnits"))
            have_tei = self._to_id_set(cur.get("teiSearchOrganisationUnits"))
        else:
            have_cap = have_view = have_tei = set()

        def add_ops(path: str, ids: Optional[Iterable[str]], existing: set[str]) -> None:
            if not ids:
                return
            for i in ids:
                if dedupe and i in existing:
                    continue
                ops.append({"op": "add", "path": f"{path}/-", "value": {"id": i}})

        add_ops(paths["capture"], capture, have_cap)
        add_ops(paths["view"], view, have_view)
        add_ops(paths["tei"], tei, have_tei)

        return {"status": "NOOP"} if not ops else self._patch(f"/api/users/{uid}", json=ops)

    def replace_user_org_unit_scopes(
        self,
        uid: str,
        *,
        capture: Optional[Iterable[str]] = None,
        view: Optional[Iterable[str]] = None,
        tei: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """
        Replace ONLY the arrays you pass; others are untouched. Uses JSON Patch 'replace'.
        """
        ops: List[Dict[str, Any]] = []
        paths = self._paths()

        if capture is not None:
            ops.append({"op": "replace", "path": paths["capture"], "value": self._ids_to_objs(capture)})
        if view is not None:
            ops.append({"op": "replace", "path": paths["view"], "value": self._ids_to_objs(view)})
        if tei is not None:
            ops.append({"op": "replace", "path": paths["tei"], "value": self._ids_to_objs(tei)})

        return {"status": "NOOP"} if not ops else self._patch(f"/api/users/{uid}", json=ops)

    def remove_user_org_unit_scopes(
        self,
        uid: str,
        *,
        capture: Optional[Iterable[str]] = None,
        view: Optional[Iterable[str]] = None,
        tei: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """
        Remove specific OU IDs from the user's scopes. Because JSON Patch 'remove'
        needs array indices, we do: GET → filter → 'replace' that array.
        """
        cur = self.get(
            uid,
            fields="organisationUnits[id],dataViewOrganisationUnits[id],teiSearchOrganisationUnits[id]",
        )
        paths = self._paths()

        def filtered(items: Optional[Iterable[Dict[str, str]]], remove_ids: Optional[Iterable[str]]):
            cur_ids = self._to_id_set(items)
            rem = set(remove_ids or [])
            keep = [{"id": x} for x in cur_ids - rem]
            return keep

        ops: List[Dict[str, Any]] = []

        if capture:
            ops.append({"op": "replace", "path": paths["capture"], "value": filtered(cur.get("organisationUnits"), capture)})
        if view:
            ops.append({"op": "replace", "path": paths["view"], "value": filtered(cur.get("dataViewOrganisationUnits"), view)})
        if tei:
            ops.append({"op": "replace", "path": paths["tei"], "value": filtered(cur.get("teiSearchOrganisationUnits"), tei)})

        return {"status": "NOOP"} if not ops else self._patch(f"/api/users/{uid}", json=ops)

    # -------- current user (me) convenience -------- #

    def _me_id(self) -> str:
        me = self._get("/api/me", params={"fields": "id"})
        me_id = me.get("id")
        if not me_id:
            raise RuntimeError("Could not resolve current user id from /api/me")
        return me_id

    def add_my_org_unit_scopes(
        self,
        *,
        capture: Optional[Iterable[str]] = None,
        view: Optional[Iterable[str]] = None,
        tei: Optional[Iterable[str]] = None,
        dedupe: bool = True,
    ) -> Dict[str, Any]:
        return self.add_user_org_unit_scopes(self._me_id(), capture=capture, view=view, tei=tei, dedupe=dedupe)

    def replace_my_org_unit_scopes(
        self,
        *,
        capture: Optional[Iterable[str]] = None,
        view: Optional[Iterable[str]] = None,
        tei: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        return self.replace_user_org_unit_scopes(self._me_id(), capture=capture, view=view, tei=tei)

    def remove_my_org_unit_scopes(
        self,
        *,
        capture: Optional[Iterable[str]] = None,
        view: Optional[Iterable[str]] = None,
        tei: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        return self.remove_user_org_unit_scopes(self._me_id(), capture=capture, view=view, tei=tei)
