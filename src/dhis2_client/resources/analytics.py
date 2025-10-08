from __future__ import annotations
from typing import Dict, Any, List, Iterable
from datetime import date
from datetime import date

from .base import Resource
from ..utils.calendar import (
    calendar_year_bounds,          # (label, {'startDate','endDate'}) for *current* year in DHIS2 calendar
    calendar_year_bounds_for,      # {'startDate','endDate'} for a specific calendar year label
    period_key,                    # sortable key for ISO period ids (YYYY / YYYYQn / YYYYMM)
    period_start_end,              # {'startDate','endDate'} for a given ISO period id
    next_period_id,                # next ISO period id
)


class Analytics(Resource):
    """
    Analytics helpers (read-only).
    """

    def get(self, *, table: str = "analytics", **params) -> Dict[str, Any]:
        return self._get(f"/api/{table}", params=params)

    def latest_period_for_level(self, de_uid: str, level: int) -> Dict[str, Any]:
        """
        Find ONE global, latest populated period for a data element across all org units
        at LEVEL-N (including their descendants), using /api/dataValueSets with startDate/endDate.
        Returns that 'existing' period and the immediate 'next' period to import.

        Return:
        {
          "meta": {
            "dataElement": "<de_uid>",
            "level": <level>,
            "periodType": "MONTHLY|QUARTERLY|YEARLY",
            "calendar": "<system calendar id>",
            "years_checked": <int>          # how many calendar years we actually scanned
          },
          "existing": { "id": "<periodId>", "startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD" } | None,
          "next":     { "id": "<periodId>", "startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD" } | None
        }
        """
        # --- system calendar (to build correct year windows) ---
        sysinfo = self._get("/api/system/info")
        calendar_id = (sysinfo.get("calendar") or "iso8601").lower()

        # --- infer periodType from DE → dataSet (validate consistency) ---
        de = self._get(
            f"/api/dataElements/{de_uid}.json",
            params={"fields": "dataSetElements[dataSet[id,name,periodType]]"},
        )

        ds_info = []
        for dse in de.get("dataSetElements", []):
            ds = dse.get("dataSet") or {}
            pt = (ds.get("periodType") or "").upper()
            if pt:
                ds_info.append({"id": ds.get("id"), "name": ds.get("name"), "periodType": pt})

        if not ds_info:
            raise ValueError(
                "Data element is not linked to any dataset (cannot infer periodType). "
                "Link it to a dataset with a supported frequency."
            )

        unique_pts = sorted({d["periodType"] for d in ds_info})
        if len(unique_pts) > 1:
            # Misconfiguration: same DE assigned to datasets with different frequencies
            details = ", ".join(f'{d["id"]} (“{d.get("name") or d["id"]}”) → {d["periodType"]}' for d in ds_info)
            raise ValueError(
                "Inconsistent DHIS2 configuration: data element is assigned to multiple datasets "
                "with different period types. Found: "
                + "; ".join(unique_pts)
                + ". Datasets: "
                + details
            )

        period_type = unique_pts[0]
        if period_type not in {"MONTHLY", "QUARTERLY", "YEARLY"}:
            raise ValueError(
                f"Unsupported periodType '{period_type}'. "
                "Supported here: MONTHLY, QUARTERLY, YEARLY."
            )

        # --- all orgUnits at requested level ---
        ous = self._get(
            "/api/organisationUnits",
            params={"level": str(level), "fields": "id", "paging": "false"},
        ).get("organisationUnits", [])
        ou_ids: List[str] = [o["id"] for o in ous]
        if not ou_ids:
            return {
                "meta": {
                    "dataElement": de_uid,
                    "level": level,
                    "periodType": period_type,
                    "calendar": calendar_id,
                    "years_checked": 0,
                },
                "existing": None,
                "next": None,
            }

        # --- helpers ---
        def _chunks(seq: Iterable[str], n: int) -> Iterable[List[str]]:
            buf: List[str] = []
            for x in seq:
                buf.append(x)
                if len(buf) == n:
                    yield buf
                    buf = []
            if buf:
                yield buf

        def _fetch_periods_window(start_iso: str, end_iso: str) -> List[str]:
            """Call dataValueSets for the window; return *period codes* that have any values."""
            collected: List[str] = []
            for batch in _chunks(ou_ids, 200):  # tune batch size if needed
                q = [
                    ("dataElement", de_uid),
                    ("children", "true"),
                    ("startDate", start_iso),
                    ("endDate", end_iso),
                    ("paging", "false"),
                ]
                for ou in batch:
                    q.append(("orgUnit", ou))
                resp = self._get("/api/dataValueSets", params=q)
                for row in resp.get("dataValues") or []:
                    pe, val = row.get("period"), row.get("value")
                    if pe and val not in (None, ""):
                        collected.append(pe)
            return collected

        # --- slide calendar years: current → older, stop when we see any period ---
        MAX_YEARS = 30
        years_checked = 0
        latest_pid = None

        cal_year_label, now_bounds = calendar_year_bounds(calendar_id, date.today())

        # 1) current calendar year
        years_checked = 1
        periods = _fetch_periods_window(now_bounds["startDate"], now_bounds["endDate"])
        if periods:
            latest_pid = max(set(periods), key=period_key)
        else:
            # 2) previous years
            for k in range(1, MAX_YEARS + 1):
                years_checked = k + 1
                bounds = calendar_year_bounds_for(calendar_id, cal_year_label - k)
                periods = _fetch_periods_window(bounds["startDate"], bounds["endDate"])
                if periods:
                    latest_pid = max(set(periods), key=period_key)
                    break

        if latest_pid is None:
            # No data in the scanned window
            return {
                "meta": {
                    "dataElement": de_uid,
                    "level": level,
                    "periodType": period_type,
                    "calendar": calendar_id,
                    "years_checked": years_checked,
                },
                "existing": None,
                "next": None,
            }

        # --- build payload: existing + next ---
        existing = {"id": latest_pid, **period_start_end(latest_pid)}
        nxt_id = next_period_id(latest_pid)
        nextp = {"id": nxt_id, **period_start_end(nxt_id)}

        return {
            "meta": {
                "dataElement": de_uid,
                "level": level,
                "periodType": period_type,
                "calendar": calendar_id,
                "years_checked": years_checked,
            },
            "existing": existing,
            "next": nextp,
        }
