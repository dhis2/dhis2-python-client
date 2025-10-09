# dhis2_client/utils/calendar.py
from __future__ import annotations
from datetime import date, timedelta, datetime
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
import calendar as _calendar
import re as _re
from datetime import date as _date, timedelta as _td, datetime as _dt
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
    """
    Return {'startDate','endDate'} (ISO yyyy-mm-dd) for common DHIS2 period ids:
      - Daily:                YYYYMMDD
      - Date range (analytics): YYYYMMDD_YYYYMMDD
      - Weekly (ISO Monday):  YYYYWww
      - Monthly:              YYYYMM
      - Quarterly:            YYYYQn
      - Yearly:               YYYY
      - SixMonthly (Jan/Jul): YYYYS1 | YYYYS2   (optional convenience)

    Notes:
    - If you’re using non-ISO weekly variants or exotic half-years, prefer passing a
      date-range (YYYYMMDD_YYYYMMDD) upstream. This helper focuses on widely used forms.
    """
    s = period_id.strip()

    # 1) Date range "YYYYMMDD_YYYYMMDD"
    m = _re.fullmatch(r"(\d{8})_(\d{8})", s)
    if m:
        sd = _dt.strptime(m.group(1), "%Y%m%d").date()
        ed = _dt.strptime(m.group(2), "%Y%m%d").date()
        if ed < sd:
            raise ValueError(f"Invalid period range (end<start): {s}")
        return {"startDate": sd.isoformat(), "endDate": ed.isoformat()}

    # 2) Daily "YYYYMMDD"
    if _re.fullmatch(r"\d{8}", s):
        d = _dt.strptime(s, "%Y%m%d").date()
        return {"startDate": d.isoformat(), "endDate": d.isoformat()}

    # 3) Weekly ISO "YYYYWww"
    m = _re.fullmatch(r"(\d{4})W(\d{2})", s)
    if m:
        y, w = int(m.group(1)), int(m.group(2))
        # Monday=1 .. Sunday=7
        start = _dt.fromisocalendar(y, w, 1).date()
        end = start + _td(days=6)
        return {"startDate": start.isoformat(), "endDate": end.isoformat()}

    # 4) Quarterly "YYYYQn"
    m = _re.fullmatch(r"(\d{4})Q([1-4])", s)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        sm = {1: 1, 2: 4, 3: 7, 4: 10}[q]
        em = {1: 3, 2: 6, 3: 9, 4: 12}[q]
        start = _date(y, sm, 1)
        end = _date(y, em, _calendar.monthrange(y, em)[1])
        return {"startDate": start.isoformat(), "endDate": end.isoformat()}

    # 5) SixMonthly "YYYYS1|S2" (Jan–Jun / Jul–Dec)
    m = _re.fullmatch(r"(\d{4})S([12])", s)
    if m:
        y, half = int(m.group(1)), int(m.group(2))
        if half == 1:
            start = _date(y, 1, 1)
            end = _date(y, 6, 30)
        else:
            start = _date(y, 7, 1)
            end = _date(y, 12, 31)
        return {"startDate": start.isoformat(), "endDate": end.isoformat()}

    # 6) Monthly "YYYYMM"
    m = _re.fullmatch(r"(\d{4})(\d{2})", s)
    if m:
        y, mm = int(m.group(1)), int(m.group(2))
        if not (1 <= mm <= 12):
            raise ValueError(f"Invalid month in period id: {s}")
        start = _date(y, mm, 1)
        end = _date(y, mm, _calendar.monthrange(y, mm)[1])
        return {"startDate": start.isoformat(), "endDate": end.isoformat()}

    # 7) Yearly "YYYY"
    if _re.fullmatch(r"\d{4}", s):
        y = int(s)
        return {"startDate": _date(y, 1, 1).isoformat(), "endDate": _date(y, 12, 31).isoformat()}

    raise ValueError(f"Unsupported or unrecognized period id: {period_id}")


def next_period_id(period_id: str) -> str:
    s = period_id.strip()

    # Daily: YYYYMMDD -> +1 day
    if _re.fullmatch(r"\d{8}", s):
        d = _dt.strptime(s, "%Y%m%d").date() + _td(days=1)
        return d.strftime("%Y%m%d")

    # Weekly ISO: YYYYWww -> next ISO week (handles year rollover)
    m = _re.fullmatch(r"(\d{4})W(\d{2})", s)
    if m:
        y, w = int(m.group(1)), int(m.group(2))
        start = _dt.fromisocalendar(y, w, 1).date()
        nxt = start + _td(days=7)
        ny, nw, _ = nxt.isocalendar()
        return f"{ny}W{nw:02d}"

    # SixMonthly (Jan–Jun / Jul–Dec): YYYYS1|S2
    m = _re.fullmatch(r"(\d{4})S([12])", s)
    if m:
        y, h = int(m.group(1)), int(m.group(2))
        return f"{y:04d}S2" if h == 1 else f"{y+1:04d}S1"

    # Quarterly: YYYYQn
    m = _re.fullmatch(r"(\d{4})Q([1-4])", s)
    if m:
        y, q = int(m.group(1)), int(m.group(2)) + 1
        return f"{y+1:04d}Q1" if q == 5 else f"{y:04d}Q{q}"

    # Monthly: YYYYMM
    m = _re.fullmatch(r"(\d{4})(\d{2})", s)
    if m:
        y, mm = int(m.group(1)), int(m.group(2)) + 1
        return f"{y+1:04d}01" if mm == 13 else f"{y:04d}{mm:02d}"

    # Yearly: YYYY
    if _re.fullmatch(r"\d{4}", s):
        return f"{int(s)+1:04d}"

    raise ValueError(f"Unsupported or unrecognized period id: {period_id}")


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

# ======================================================================
#                       FIXED-PERIOD GENERATOR
# ======================================================================

@dataclass
class PeriodResult:
    period_id: Optional[str]   # canonical when stable (e.g., 2025W41, 202509, 2025Q3…)
    period_range: str          # always safe: YYYYMMDD_YYYYMMDD
    startDate: str             # ISO YYYY-MM-DD
    endDate: str               # ISO YYYY-MM-DD

def _iso(d: date) -> str:
    return d.isoformat()

def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")

# ---- calendar conversion helpers (best-effort) ------------------------------

def _have_conv(cal: str) -> bool:
    cal = (cal or "iso8601").lower()
    return ((cal in ("iso8601","gregorian","buddhist")) or
            (cal == "ethiopian" and ethiopian) or
            (cal == "coptic" and coptic) or
            (cal == "islamic" and islamic) or
            (cal in ("persian","jalali") and jalali))

def _to_greg(cal: str, y: int, m: int, d: int) -> date:
    cal = (cal or "iso8601").lower()
    if cal in ("iso8601","gregorian","buddhist"):
        return date(y, m, d)
    if cal == "ethiopian" and ethiopian:
        gy, gm, gd = ethiopian.to_gregorian(y, m, d); return date(gy, gm, gd)
    if cal == "coptic" and coptic:
        gy, gm, gd = coptic.to_gregorian(y, m, d); return date(gy, gm, gd)
    if cal == "islamic" and islamic:
        gy, gm, gd = islamic.to_gregorian(y, m, d); return date(gy, gm, gd)
    if cal in ("persian","jalali") and jalali:
        gy, gm, gd = jalali.to_gregorian(y, m, d); return date(gy, gm, gd)
    return date(y, m, d)

def _from_greg(cal: str, g: date) -> Tuple[int,int,int]:
    cal = (cal or "iso8601").lower()
    if cal in ("iso8601","gregorian","buddhist"):
        return g.year, g.month, g.day
    if cal == "ethiopian" and ethiopian:
        return ethiopian.from_gregorian(g.year, g.month, g.day)
    if cal == "coptic" and coptic:
        return coptic.from_gregorian(g.year, g.month, g.day)
    if cal == "islamic" and islamic:
        return islamic.from_gregorian(g.year, g.month, g.day)
    if cal in ("persian","jalali") and jalali:
        return jalali.from_gregorian(g.year, g.month, g.day)
    return g.year, g.month, g.day

def _greg_month_end(y: int, m: int) -> date:
    if m == 12:
        return date(y, 12, 31)
    return date(y, m + 1, 1) - timedelta(days=1)

# ---- month bounds in the configured calendar --------------------------------
def month_bounds(calendar_id: str, year_label: int, month_index: int) -> Tuple[date, date]:
    """
    Returns (greg_start, greg_end) for the given calendar's (year_label, month_index).
    month_index is 1..12 in that calendar.
    """
    cal = (calendar_id or "iso8601").lower()
    start_g = _to_greg(cal, year_label, month_index, 1)
    # next month in that calendar
    if month_index == 12:
        next_y, next_m = year_label + 1, 1
    else:
        next_y, next_m = year_label, month_index + 1
    next_start_g = _to_greg(cal, next_y, next_m, 1)
    end_g = next_start_g - timedelta(days=1)
    return start_g, end_g

# ---- quarter/half-year using calendar months --------------------------------
def quarter_bounds(calendar_id: str, year_label: int, q: int) -> Tuple[date, date]:
    sm = {1:1, 2:4, 3:7, 4:10}[q]
    em = {1:3, 2:6, 3:9, 4:12}[q]
    s, _ = month_bounds(calendar_id, year_label, sm)
    _, e = month_bounds(calendar_id, year_label, em)
    return s, e

def sixmonthly_bounds(calendar_id: str, year_label: int, variant: str, half: int) -> Tuple[date, date]:
    """
    Variants:
    - SixMonthly:         H1=(1..6),  H2=(7..12)
    - SixMonthlyApril:    H1=(4..9),  H2=(10..3) next year
    - SixMonthlyNovember: H1=(11..4), H2=(5..10)
    """
    cal = (calendar_id or "iso8601").lower()
    if variant == "SixMonthly":
        months = (1,6) if half == 1 else (7,12)
        y = year_label
        s,_ = month_bounds(cal, y, months[0])
        _,e = month_bounds(cal, y, months[1])
        return s,e

    if variant == "SixMonthlyApril":
        if half == 1:
            y = year_label
            s,_ = month_bounds(cal, y, 4);  _,e = month_bounds(cal, y, 9)
        else:
            y = year_label
            s,_ = month_bounds(cal, y, 10)
            _,e = month_bounds(cal, y + 1, 3)
        return s,e

    # SixMonthlyNovember
    if half == 1:
        s,_ = month_bounds(cal, year_label - 1, 11)
        _,e = month_bounds(cal, year_label, 4)
    else:
        s,_ = month_bounds(cal, year_label, 5)
        _,e = month_bounds(cal, year_label, 10)
    return s,e

# ---- weekly & biweekly (weekday-based; calendar-agnostic) -------------------
_WEEK_START = {
    "Weekly": 0,               # Monday
    "WeeklyWednesday": 2,
    "WeeklyThursday": 3,
    "WeeklySaturday": 5,
    "WeeklySunday": 6,
}

def _closed_week_bounds(today: date, week_start: int) -> Tuple[date, date]:
    delta = (today.weekday() - week_start) % 7
    curr_start = today - timedelta(days=delta)
    curr_end = curr_start + timedelta(days=6)
    if curr_end < today:
        return curr_start, curr_end
    prev_start = curr_start - timedelta(days=7)
    return prev_start, prev_start + timedelta(days=6)

def _latest_closed_biweekly(today: date) -> Tuple[date, date]:
    # ISO Monday anchored two-week blocks
    w_start, w_end = _closed_week_bounds(today, 0)  # ISO Monday
    _, iso_week, _ = w_end.isocalendar()
    if iso_week % 2 == 0:
        bi_end = w_end
    else:
        bi_end = w_end - timedelta(days=7)
    bi_start = bi_end - timedelta(days=13)
    return bi_start, bi_end

# ---- PUBLIC: latest closed period for a DHIS2 fixed type --------------------
def latest_closed_period(
    period_type: str,
    *,
    today: Optional[date] = None,
    calendar_id: str = "iso8601",
) -> PeriodResult:
    """
    Compute the latest *closed* period for a DHIS2 fixed period type,
    respecting the configured DHIS2 calendar for month/quarter/half-year/financial types
    (when conversion libraries are available). For weekly variants, rules are weekday-based.

    Returns:
      PeriodResult(period_id=?, period_range='YYYYMMDD_YYYYMMDD', startDate='YYYY-MM-DD', endDate='YYYY-MM-DD')
    """
    pt = period_type.strip()
    today = today or date.today()
    cal = (calendar_id or "iso8601").lower()

    # ---- Daily
    if pt == "Daily":
        endd = today - timedelta(days=1)
        startd = endd
        return PeriodResult(_yyyymmdd(endd), f"{_yyyymmdd(startd)}_{_yyyymmdd(endd)}", _iso(startd), _iso(endd))

    # ---- Weekly & variants (calendar-agnostic)
    if pt in _WEEK_START:
        s, e = _closed_week_bounds(today, _WEEK_START[pt])
        pid = None
        if pt == "Weekly":
            iso_year, iso_week, _ = e.isocalendar()
            pid = f"{iso_year}W{iso_week:02d}"
        return PeriodResult(pid, f"{_yyyymmdd(s)}_{_yyyymmdd(e)}", _iso(s), _iso(e))

    if pt == "BiWeekly":
        s, e = _latest_closed_biweekly(today)
        return PeriodResult(None, f"{_yyyymmdd(s)}_{_yyyymmdd(e)}", _iso(s), _iso(e))

    # ---- Determine current calendar year label for calendar-based types
    year_label, _ = calendar_year_bounds(cal, today)

    # ---- Monthly
    if pt == "Monthly":
        y, m, _ = _from_greg(cal, today)
        if m == 1:
            y -= 1; m = 12
        else:
            m -= 1
        s, e = month_bounds(cal, y, m)
        pid = f"{s.year}{s.month:02d}" if cal in ("iso8601","gregorian","buddhist") else None
        return PeriodResult(pid, f"{_yyyymmdd(s)}_{_yyyymmdd(e)}", _iso(s), _iso(e))

    # ---- BiMonthly: pairs (1-2),(3-4),...,(11-12) in the chosen calendar
    if pt == "BiMonthly":
        y, m, _ = _from_greg(cal, today)
        # move to previously closed calendar month
        if m == 1:
            y -= 1; m_prev = 12
        else:
            m_prev = m - 1
        # pair start is odd month of the pair
        pair_start = m_prev - 1 if m_prev % 2 == 0 else m_prev
        s, _ = month_bounds(cal, y, pair_start)
        # end is end of the next month in same calendar
        _, e = month_bounds(cal, y if pair_start != 12 else y, pair_start + 1 if pair_start < 12 else 12)
        # ID (only when ISO/Gregorian): e.g., 2025B1..B6
        idx = (pair_start + 1) // 2
        pid = f"{s.year}B{idx}" if cal in ("iso8601","gregorian","buddhist") else None
        return PeriodResult(pid, f"{_yyyymmdd(s)}_{_yyyymmdd(e)}", _iso(s), _iso(e))

    # ---- Quarterly
    if pt == "Quarterly":
        gy, gm, _ = _from_greg(cal, today)
        q_curr = ((gm - 1) // 3) + 1
        q_closed = q_curr - 1 if q_curr > 1 else 4
        yq = year_label if q_curr > 1 else (year_label - 1)
        s, e = quarter_bounds(cal, yq, q_closed)
        pid = f"{s.year}Q{q_closed}" if cal in ("iso8601","gregorian","buddhist") else None
        return PeriodResult(pid, f"{_yyyymmdd(s)}_{_yyyymmdd(e)}", _iso(s), _iso(e))

    # ---- SixMonthly, SixMonthlyApril, SixMonthlyNovember
    if pt in ("SixMonthly","SixMonthlyApril","SixMonthlyNovember"):
        candidates: List[Tuple[date,int,int]] = []  # (end, year_label, half)
        for h in (1,2):
            s, e = sixmonthly_bounds(cal, year_label, pt, h)
            if e < today:
                candidates.append((e, year_label, h))
        if not candidates:
            yl = year_label - 1
            for h in (1,2):
                s, e = sixmonthly_bounds(cal, yl, pt, h)
                if e < today:
                    candidates.append((e, yl, h))
        candidates.sort()
        _, yl_sel, h_sel = candidates[-1]
        s, e = sixmonthly_bounds(cal, yl_sel, pt, h_sel)
        if pt == "SixMonthly":
            pid = f"{s.year}S{1 if _from_greg(cal, s)[1] == 1 else 2}" if cal in ("iso8601","gregorian","buddhist") else None
        elif pt == "SixMonthlyApril":
            pid = f"{s.year}AprilS{1 if _from_greg(cal, s)[1] == 4 else 2}" if cal in ("iso8601","gregorian","buddhist") else None
        else:
            pid = f"{s.year}NovS{1 if _from_greg(cal, s)[1] == 11 else 2}" if cal in ("iso8601","gregorian","buddhist") else None
        return PeriodResult(pid, f"{_yyyymmdd(s)}_{_yyyymmdd(e)}", _iso(s), _iso(e))

    # ---- Yearly
    if pt == "Yearly":
        y = year_label - 1
        b = calendar_year_bounds_for(cal, y)
        s, e = date.fromisoformat(b["startDate"]), date.fromisoformat(b["endDate"])
        pid = str(s.year) if cal in ("iso8601","gregorian","buddhist") else None
        return PeriodResult(pid, f"{_yyyymmdd(s)}_{_yyyymmdd(e)}", b["startDate"], b["endDate"])

    # ---- TwoYearly
    if pt == "TwoYearly":
        y1 = year_label - 2
        b1 = calendar_year_bounds_for(cal, y1)
        b2 = calendar_year_bounds_for(cal, y1 + 1)
        s = date.fromisoformat(b1["startDate"])
        e = date.fromisoformat(b2["endDate"])
        pid = f"{s.year}{e.year}" if cal in ("iso8601","gregorian","buddhist") else None
        return PeriodResult(pid, f"{_yyyymmdd(s)}_{_yyyymmdd(e)}", _iso(s), _iso(e))

    # ---- Financial years (anchor months)
    if pt in ("FinancialApril","FinancialJuly","FinancialOctober","FinancialNovember"):
        anchor = {"FinancialApril":4, "FinancialJuly":7, "FinancialOctober":10, "FinancialNovember":11}[pt]
        # “This year’s anchor” in configured calendar:
        this_anchor_g = _to_greg(cal, year_label, anchor, 1)
        if today >= this_anchor_g:
            # Latest closed FY is previous: [anchor of (year_label-1)] .. [anchor of (year_label) - 1 day]
            fy_start = _to_greg(cal, year_label - 1, anchor, 1)
            next_anchor = _to_greg(cal, year_label, anchor, 1)
            fy_end = next_anchor - timedelta(days=1)
            id_year = _from_greg("iso8601", fy_start)[0]
        else:
            fy_start = _to_greg(cal, year_label - 2, anchor, 1)
            next_anchor = _to_greg(cal, year_label - 1, anchor, 1)
            fy_end = next_anchor - timedelta(days=1)
            id_year = _from_greg("iso8601", fy_start)[0]
        label = pt.replace("Financial","")
        pid = f"{id_year}{label}" if cal in ("iso8601","gregorian","buddhist") else None
        return PeriodResult(pid, f"{_yyyymmdd(fy_start)}_{_yyyymmdd(fy_end)}", _iso(fy_start), _iso(fy_end))

    raise ValueError(f"Unsupported or unknown period type: {period_type}")
