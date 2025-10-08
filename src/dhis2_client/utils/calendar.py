# dhis2_client/utils/calendar.py
from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, Tuple
import importlib

def _opt_import(name: str):
    try:
        return importlib.import_module(name)
    except Exception:
        return None

ethiopian = _opt_import("convertdate.ethiopian")
coptic    = _opt_import("convertdate.coptic")
islamic   = _opt_import("convertdate.islamic")
jalali    = _opt_import("convertdate.jalali")  # Persian/Jalali

# --- Period math (DHIS2 ISO period ids) --------------------------------------

def period_start_end(period_id: str) -> Dict[str, str]:
    """Return {'startDate','endDate'} (ISO) for YEARLY(YYYY), QUARTERLY(YYYYQn), MONTHLY(YYYYMM)."""
    import calendar
    y = int(period_id[:4])
    if len(period_id) == 4:  # YEARLY
        from datetime import date as d
        return {"startDate": d(y, 1, 1).isoformat(), "endDate": d(y, 12, 31).isoformat()}
    if "Q" in period_id:     # QUARTERLY
        from datetime import date as d
        q = int(period_id[-1])
        sm, em = {1: 1, 2: 4, 3: 7, 4: 10}[q], {1: 3, 2: 6, 3: 9, 4: 12}[q]
        return {"startDate": d(y, sm, 1).isoformat(),
                "endDate":   d(y, em, calendar.monthrange(y, em)[1]).isoformat()}
    # MONTHLY
    from datetime import date as d
    m = int(period_id[4:6])
    return {"startDate": d(y, m, 1).isoformat(),
            "endDate":   d(y, m, __import__("calendar").monthrange(y, m)[1]).isoformat()}

def next_period_id(period_id: str) -> str:
    """Return the next sequential period id for YEARLY/QUARTERLY/MONTHLY."""
    if len(period_id) == 4:          # YEARLY
        return f"{int(period_id) + 1:04d}"
    if "Q" in period_id:             # QUARTERLY
        y, q = int(period_id[:4]), int(period_id[-1]) + 1
        return f"{(y+1):04d}Q1" if q == 5 else f"{y:04d}Q{q}"
    # MONTHLY
    y, m = int(period_id[:4]), int(period_id[4:6]) + 1
    return f"{(y+1):04d}01" if m == 13 else f"{y:04d}{m:02d}"

def period_key(period_id: str) -> Tuple[int, int, int]:
    """Sortable key so max(periods, key=period_key) gives the latest."""
    if len(period_id) == 4: return (int(period_id), 0, 0)
    if "Q" in period_id:    return (int(period_id[:4]), int(period_id[-1]), 0)
    return (int(period_id[:4]), int(period_id[4:6]), 0)

# --- Calendar year bounds (system calendar aware) ----------------------------

def calendar_year_bounds(calendar_id: str, today: date) -> Tuple[int, Dict[str, str]]:
    """
    Return (calendar_year_label, {'startDate','endDate'}) for the current year
    in the given DHIS2 calendar (iso8601, gregorian, buddhist, ethiopian, coptic, islamic, persian/jalali).
    """
    cal = (calendar_id or "iso8601").lower()

    def _greg_bounds(y: int) -> Dict[str, str]:
        return {"startDate": date(y, 1, 1).isoformat(), "endDate": date(y, 12, 31).isoformat()}

    if cal in ("iso8601", "gregorian", "buddhist"):
        return today.year, _greg_bounds(today.year)

    if cal == "ethiopian" and ethiopian:
        ey, em, ed = ethiopian.from_gregorian(today.year, today.month, today.day)
        gy, gm, gd = ethiopian.to_gregorian(ey, 1, 1)
        ny, nm, nd = ethiopian.to_gregorian(ey + 1, 1, 1)
        end = date(ny, nm, nd) - timedelta(days=1)
        return ey, {"startDate": date(gy, gm, gd).isoformat(), "endDate": end.isoformat()}

    if cal == "coptic" and coptic:
        cy, cm, cd = coptic.from_gregorian(today.year, today.month, today.day)
        gy, gm, gd = coptic.to_gregorian(cy, 1, 1)
        ny, nm, nd = coptic.to_gregorian(cy + 1, 1, 1)
        end = date(ny, nm, nd) - timedelta(days=1)
        return cy, {"startDate": date(gy, gm, gd).isoformat(), "endDate": end.isoformat()}

    if cal == "islamic" and islamic:
        hy, hm, hd = islamic.from_gregorian(today.year, today.month, today.day)
        gy, gm, gd = islamic.to_gregorian(hy, 1, 1)
        ny, nm, nd = islamic.to_gregorian(hy + 1, 1, 1)
        end = date(ny, nm, nd) - timedelta(days=1)
        return hy, {"startDate": date(gy, gm, gd).isoformat(), "endDate": end.isoformat()}

    if cal in ("persian", "jalali") and jalali:
        jy, jm, jd = jalali.from_gregorian(today.year, today.month, today.day)
        gy, gm, gd = jalali.to_gregorian(jy, 1, 1)
        ny, nm, nd = jalali.to_gregorian(jy + 1, 1, 1)
        end = date(ny, nm, nd) - timedelta(days=1)
        return jy, {"startDate": date(gy, gm, gd).isoformat(), "endDate": end.isoformat()}

    # Fallback: treat as Gregorian if convert libs missing/unknown calendar
    return today.year, _greg_bounds(today.year)

def calendar_year_bounds_for(calendar_id: str, base_year_label: int) -> Dict[str, str]:
    """
    Return {'startDate','endDate'} for a *specific* calendar year label.
    (Used when sliding back year-by-year in the configured system calendar.)
    """
    cal = (calendar_id or "iso8601").lower()

    def _greg_bounds(y: int) -> Dict[str, str]:
        return {"startDate": date(y, 1, 1).isoformat(), "endDate": date(y, 12, 31).isoformat()}

    if cal in ("iso8601", "gregorian", "buddhist"):
        return _greg_bounds(base_year_label)

    if cal == "ethiopian" and ethiopian:
        gy, gm, gd = ethiopian.to_gregorian(base_year_label, 1, 1)
        ny, nm, nd = ethiopian.to_gregorian(base_year_label + 1, 1, 1)
        return {"startDate": date(gy, gm, gd).isoformat(),
                "endDate": (date(ny, nm, nd) - timedelta(days=1)).isoformat()}

    if cal == "coptic" and coptic:
        gy, gm, gd = coptic.to_gregorian(base_year_label, 1, 1)
        ny, nm, nd = coptic.to_gregorian(base_year_label + 1, 1, 1)
        return {"startDate": date(gy, gm, gd).isoformat(),
                "endDate": (date(ny, nm, nd) - timedelta(days=1)).isoformat()}

    if cal == "islamic" and islamic:
        gy, gm, gd = islamic.to_gregorian(base_year_label, 1, 1)
        ny, nm, nd = islamic.to_gregorian(base_year_label + 1, 1, 1)
        return {"startDate": date(gy, gm, gd).isoformat(),
                "endDate": (date(ny, nm, nd) - timedelta(days=1)).isoformat()}

    if cal in ("persian", "jalali") and jalali:
        gy, gm, gd = jalali.to_gregorian(base_year_label, 1, 1)
        ny, nm, nd = jalali.to_gregorian(base_year_label + 1, 1, 1)
        return {"startDate": date(gy, gm, gd).isoformat(),
                "endDate": (date(ny, nm, nd) - timedelta(days=1)).isoformat()}

    return _greg_bounds(base_year_label)
