from __future__ import annotations

from typing import Dict, Any, Optional, List, Iterable
from dataclasses import dataclass

from .base import Resource

# ---- Access masks (centralized) ----------------------------------------

DATA_READ  = "rwr-----"   # data: rwr,  meta: rw
DATA_WRITE = "rwrw----"   # data: rwrw, meta: rw (typical for capture)
META_READ  = "rw-------"  # meta: r,  data: -
META_WRITE = "rw-------"  # meta: rw, data: -
NO_ACCESS  = "--------"


# ---- Parameterized defaults (centralized) ------------------------------

@dataclass(frozen=True)
class SharingDefaults:
    public_access: str = META_WRITE
    allow_public_access: bool = True
    allow_external_access: bool = False


DEFAULTS = SharingDefaults()


# ---- Sharing resource --------------------------------------------------

class Sharing(Resource):
    """
    Explicit API for DHIS2 /api/sharing with centralized defaults and safe merging.
    """

    # ---------- Low-level primitives ----------

    def get(self, *, object_type: str, object_id: str) -> Dict[str, Any]:
        return self._get("/api/sharing", params={"type": object_type, "id": object_id})

    def _build_body(
        self,
        *,
        public_access: str,
        user_accesses: Optional[List[Dict[str, str]]] = None,
        user_group_accesses: Optional[List[Dict[str, str]]] = None,
        defaults: SharingDefaults = DEFAULTS,
    ) -> Dict[str, Any]:
        return {
            "meta": {
                "allowPublicAccess": defaults.allow_public_access,
                "allowExternalAccess": defaults.allow_external_access,
            },
            "object": {
                "publicAccess": public_access,
                "userGroupAccesses": user_group_accesses or [],
                "userAccesses": user_accesses or [],
            },
        }

    def _post_sharing(
        self,
        *,
        object_type: str,
        object_id: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        # NOTE: base.Resource._post doesn't accept params; call client directly.
        return self._post("/api/sharing", params={"type": object_type, "id": object_id}, json=body)

    # ---------- Merge helpers (safe) ----------

    def _current(self, *, object_type: str, object_id: str) -> Dict[str, Any]:
        return (self.get(object_type=object_type, object_id=object_id) or {}).get("object", {}) or {}

    @staticmethod
    def _merge_accesses(
        current: List[Dict[str, str]],
        updates: Dict[str, str],   # id -> access
    ) -> List[Dict[str, str]]:
        # Merge by id (preserve others)
        merged: Dict[str, str] = {u.get("id"): u.get("access", DATA_READ) for u in (current or [])}
        merged.update(updates or {})
        return [{"id": i, "access": a} for i, a in merged.items()]

    # ---------- High-level API ----------

    def set(
        self,
        *,
        object_type: str,
        object_id: str,
        public_access: str = DEFAULTS.public_access,
        user_group_accesses: Optional[List[Dict[str, str]]] = None,
        user_accesses: Optional[List[Dict[str, str]]] = None,
        allow_public_access: Optional[bool] = None,
        allow_external_access: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Replace the entire sharing definition for an object.
        """
        defaults = SharingDefaults(
            public_access,
            allow_public_access if allow_public_access is not None else DEFAULTS.allow_public_access,
            allow_external_access if allow_external_access is not None else DEFAULTS.allow_external_access,
        )
        body = self._build_body(
            public_access=public_access,
            user_accesses=user_accesses,
            user_group_accesses=user_group_accesses,
            defaults=defaults,
        )
        return self._post_sharing(object_type=object_type, object_id=object_id, body=body)

    def grant_self_access(
        self,
        *,
        object_type: str,
        object_id: str,
        access: str = DATA_WRITE,
        public_access: Optional[str] = None,  # None => keep current
        defaults: SharingDefaults = DEFAULTS,
    ) -> Dict[str, Any]:
        """
        Give the current user (/api/me) a specific access mask on an object, merging with existing.
        """
        me = self._get("/api/me", params={"fields": "id"})
        me_id = me.get("id")
        if not me_id:
            raise RuntimeError("Could not resolve current user id from /api/me")

        obj = self._current(object_type=object_type, object_id=object_id)
        cur_users  = obj.get("userAccesses", []) or []
        cur_groups = obj.get("userGroupAccesses", []) or []
        cur_public = obj.get("publicAccess", DEFAULTS.public_access)

        user_updates = {me_id: access}
        merged_users = self._merge_accesses(cur_users, user_updates)

        body = self._build_body(
            public_access=(cur_public if public_access is None else public_access),
            user_accesses=merged_users,
            user_group_accesses=cur_groups,
            defaults=defaults,
        )
        return self._post_sharing(object_type=object_type, object_id=object_id, body=body)

    def set_public_access(
        self,
        *,
        object_type: str,
        object_id: str,
        public_access: str,
        defaults: SharingDefaults = DEFAULTS,
    ) -> Dict[str, Any]:
        """Change only publicAccess, keep users/groups as-is."""
        obj = self._current(object_type=object_type, object_id=object_id)
        body = self._build_body(
            public_access=public_access,
            user_accesses=obj.get("userAccesses") or [],
            user_group_accesses=obj.get("userGroupAccesses") or [],
            defaults=defaults,
        )
        return self._post_sharing(object_type=object_type, object_id=object_id, body=body)

    def grant_access(
        self,
        *,
        object_type: str,
        object_id: str,
        user_ids: Optional[Iterable[str]] = None,
        user_group_ids: Optional[Iterable[str]] = None,
        access: str = DATA_WRITE,
        keep_public: bool = True,
        defaults: SharingDefaults = DEFAULTS,
    ) -> Dict[str, Any]:
        """
        Grant the same access mask to many users/groups at once, merging with current sharing.
        """
        obj = self._current(object_type=object_type, object_id=object_id)
        cur_users  = obj.get("userAccesses", []) or []
        cur_groups = obj.get("userGroupAccesses", []) or []
        cur_public = obj.get("publicAccess", DEFAULTS.public_access)

        user_updates  = {uid: access for uid in (user_ids or [])}
        group_updates = {gid: access for gid in (user_group_ids or [])}

        merged_users  = self._merge_accesses(cur_users, user_updates)
        merged_groups = self._merge_accesses(cur_groups, group_updates)

        body = self._build_body(
            public_access=(cur_public if keep_public else NO_ACCESS),
            user_accesses=merged_users,
            user_group_accesses=merged_groups,
            defaults=defaults,
        )
        return self._post_sharing(object_type=object_type, object_id=object_id, body=body)

    # ---------- Dataset sugar ----------

    def grant_self_data_write_on_dataset(self, dataset_id: str, access: str = DATA_WRITE) -> Dict[str, Any]:
        """Grant self data write on a dataSet."""
        return self.grant_self_access(object_type="dataSet", object_id=dataset_id, access=access)

    def set_dataset_data_write(
        self,
        dataset_id: str,
        *,
        user_group_ids: Optional[Iterable[str]] = None,
        user_ids: Optional[Iterable[str]] = None,
        public_access: str = DEFAULTS.public_access,
        defaults: SharingDefaults = DEFAULTS,
    ) -> Dict[str, Any]:
        """Give users/groups data-write on a dataSet; merges with current."""
        def _acc_list(ids: Optional[Iterable[str]]):
            return ([{"id": i, "access": DATA_WRITE} for i in ids] if ids else [])

        desired_users  = _acc_list(user_ids)
        desired_groups = _acc_list(user_group_ids)

        obj = self._current(object_type="dataSet", object_id=dataset_id)
        merged_users  = self._merge_accesses(obj.get("userAccesses") or [], {ua["id"]: ua["access"] for ua in desired_users})
        merged_groups = self._merge_accesses(obj.get("userGroupAccesses") or [], {ga["id"]: ga["access"] for ga in desired_groups})

        body = self._build_body(
            public_access=public_access,
            user_accesses=merged_users,
            user_group_accesses=merged_groups,
            defaults=defaults,
        )
        return self._post_sharing(object_type="dataSet", object_id=dataset_id, body=body)
