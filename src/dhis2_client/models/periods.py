# src/dhis2_client/models/periods.py
import re
from datetime import date, datetime
from typing import Dict, Set

PERIOD_TYPES_INFO: Dict[str, Dict[str, object]] = {
    "Daily": {"isoDuration": "P1D", "isoFormat": "yyyyMMdd", "frequencyOrder": 1},
    "Weekly": {"isoDuration": "P7D", "isoFormat": "yyyyWn", "frequencyOrder": 7},
    "WeeklyWednesday": {"isoDuration": "P7D", "isoFormat": "yyyyWedWn", "frequencyOrder": 7},
    "WeeklyThursday": {"isoDuration": "P7D", "isoFormat": "yyyyThuWn", "frequencyOrder": 7},
    "WeeklySaturday": {"isoDuration": "P7D", "isoFormat": "yyyySatWn", "frequencyOrder": 7},
    "WeeklySunday": {"isoDuration": "P7D", "isoFormat": "yyyySunWn", "frequencyOrder": 7},
    "BiWeekly": {"isoDuration": "P14D", "isoFormat": "yyyyBiWn", "frequencyOrder": 14},
    "Monthly": {"isoDuration": "P1M", "isoFormat": "yyyyMM", "frequencyOrder": 30},
    "BiMonthly": {"isoDuration": "P2M", "isoFormat": "yyyyMMB", "frequencyOrder": 61},
    "Quarterly": {"isoDuration": "P3M", "isoFormat": "yyyyQn", "frequencyOrder": 91},
    "QuarterlyNov": {"isoDuration": "P3M", "isoFormat": "yyyyNovQn", "frequencyOrder": 91},
    "SixMonthly": {"isoDuration": "P6M", "isoFormat": "yyyySn", "frequencyOrder": 182},
    "SixMonthlyApril": {"isoDuration": "P6M", "isoFormat": "yyyyAprilSn", "frequencyOrder": 182},
    "SixMonthlyNov": {"isoDuration": "P6M", "isoFormat": "yyyyNovSn", "frequencyOrder": 182},
    "Yearly": {"isoDuration": "P1Y", "isoFormat": "yyyy", "frequencyOrder": 365},
    "FinancialApril": {"isoDuration": "P1Y", "isoFormat": "yyyyApril", "frequencyOrder": 365},
    "FinancialJuly": {"isoDuration": "P1Y", "isoFormat": "yyyyJuly", "frequencyOrder": 365},
    "FinancialSep": {"isoDuration": "P1Y", "isoFormat": "yyyySep", "frequencyOrder": 365},
    "FinancialOct": {"isoDuration": "P1Y", "isoFormat": "yyyyOct", "frequencyOrder": 365},
    "FinancialNov": {"isoDuration": "P1Y", "isoFormat": "yyyyNov", "frequencyOrder": 365},
}
PERIOD_TYPES: Set[str] = set(PERIOD_TYPES_INFO.keys())


def _iso_week_ok(year: int, week: int) -> bool:
    """Return True if (year, week) is a valid ISO week."""
    try:
        # ISO weeks: the Monday of that week must be valid
        datetime.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u")
        return 1 <= week <= 53
    except ValueError:
        return False


def _year_ok(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}", value))


def validate_period(period_type: str, value: str) -> None:
    """Validate a DHIS2 period string against a DHIS2 period type."""
    if period_type not in PERIOD_TYPES:
        raise ValueError(f"Unknown period type '{period_type}'")

    if period_type == "Daily":
        if not re.fullmatch(r"\d{8}", value):
            raise ValueError("Daily must be 'yyyyMMdd'")
        datetime.strptime(value, "%Y%m%d")
        return True

    if period_type == "Monthly":
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError("Monthly must be 'yyyyMM'")
        datetime.strptime(value, "%Y%m")
        return True

    if period_type == "Quarterly":
        if not re.fullmatch(r"\d{4}Q[1-4]", value):
            raise ValueError("Quarterly must be 'yyyyQn'")
        return True

    if period_type == "SixMonthly":
        if not re.fullmatch(r"\d{4}S[12]", value):
            raise ValueError("SixMonthly must be 'yyyySn'")
        return True

    if period_type == "Yearly":
        if not _year_ok(value):
            raise ValueError("Yearly must be 'yyyy'")
        return True

    if period_type == "BiMonthly":
        if not re.fullmatch(r"\d{6}B", value):
            raise ValueError("BiMonthly must be 'yyyyMMB' where MM is odd")
        mm = int(value[4:6])
        if mm not in (1, 3, 5, 7, 9, 11):
            raise ValueError("BiMonthly MM must be odd (01,03,05,07,09,11)")
        return True

    if period_type == "Weekly":
        m = re.fullmatch(r"(\d{4})W(\d{2})", value)
        if not m:
            raise ValueError("Weekly must be 'yyyyWnn'")
        year, week = int(m.group(1)), int(m.group(2))
        if not _iso_week_ok(year, week):
            raise ValueError("Week number must be 01..53")
        return True

    if period_type in {"BiWeekly"}:
        if not re.fullmatch(r"\d{4}BiW\d{1,2}", value):
            raise ValueError("BiWeekly must be 'yyyyBiWn'")
        return True

    if period_type in {
        "WeeklyWednesday",
        "WeeklyThursday",
        "WeeklySaturday",
        "WeeklySunday",
    }:
        dow = {
            "WeeklyWednesday": "Wed",
            "WeeklyThursday": "Thu",
            "WeeklySaturday": "Sat",
            "WeeklySunday": "Sun",
        }[period_type]
        if not re.fullmatch(rf"\d{{4}}{dow}W\d{{1,2}}", value):
            raise ValueError(f"{period_type} must be 'yyyy{dow}Wn'")
        return True

    if period_type == "QuarterlyNov":
        if not re.fullmatch(r"\d{4}NovQ[1-4]", value):
            raise ValueError("QuarterlyNov must be 'yyyyNovQn'")
        return True

    if period_type == "SixMonthlyApril":
        if not re.fullmatch(r"\d{4}AprilS[12]", value):
            raise ValueError("SixMonthlyApril must be 'yyyyAprilSn'")
        return True

    if period_type == "SixMonthlyNov":
        if not re.fullmatch(r"\d{4}NovS[12]", value):
            raise ValueError("SixMonthlyNov must be 'yyyyNovSn'")
        return True

    if period_type in {
        "FinancialApril",
        "FinancialJuly",
        "FinancialSep",
        "FinancialOct",
        "FinancialNov",
    }:
        suffix = period_type.replace("Financial", "")
        if not re.fullmatch(rf"\d{{4}}{suffix}", value):
            raise ValueError(f"{period_type} must be 'yyyy{suffix}'")
        return True


def format_period(period_type: str, d: date) -> str:
    """Format a Python date into a DHIS2 period string for the given period type."""
    if period_type == "Daily":
        return d.strftime("%Y%m%d")

    if period_type == "Monthly":
        return d.strftime("%Y%m")

    if period_type == "Quarterly":
        q = (d.month - 1) // 3 + 1
        return f"{d.year}Q{q}"

    if period_type == "SixMonthly":
        s = 1 if d.month <= 6 else 2
        return f"{d.year}S{s}"

    if period_type == "Yearly":
        return f"{d.year}"

    if period_type == "Weekly":
        iso = d.isocalendar()
        try:
            year, week = iso.year, iso.week
        except AttributeError:
            year, week = iso[0], iso[1]
        return f"{year}W{week:02d}"

    if period_type == "BiMonthly":
        # DHIS2 encodes bimonthly by the FIRST month of the 2-month period, with 'B' suffix
        mm = d.month if d.month % 2 == 1 else d.month - 1
        return f"{d.year}{mm:02d}B"

    if period_type == "QuarterlyNov":
        # Q1: Nov–Jan, Q2: Feb–Apr, Q3: May–Jul, Q4: Aug–Oct
        if d.month >= 11:
            start_year, q = d.year, 1
        elif d.month in (2, 3, 4):
            start_year, q = d.year - 1, 2
        elif d.month in (5, 6, 7):
            start_year, q = d.year - 1, 3
        else:
            start_year, q = (d.year - 1, 4) if d.month in (8, 9, 10) else (d.year - 1, 1)
        return f"{start_year}NovQ{q}"

    if period_type == "SixMonthlyApril":
        # S1: Apr–Sep (year same as date if month in 4..9)
        # S2: Oct–Mar (cross-year; if month <= 3 then start_year = year-1)
        if 4 <= d.month <= 9:
            start_year, s = d.year, 1
        else:
            start_year, s = (d.year - 1, 2) if d.month <= 3 else (d.year, 2)
        return f"{start_year}AprilS{s}"

    if period_type == "SixMonthlyNov":
        # S1: Nov–Apr (cross-year)
        # S2: May–Oct
        if d.month >= 11 or d.month <= 4:
            start_year, s = (d.year, 1) if d.month >= 11 else (d.year - 1, 1)
        else:
            start_year, s = d.year, 2
        return f"{start_year}NovS{s}"

    if period_type in {
        "FinancialApril",
        "FinancialJuly",
        "FinancialSep",
        "FinancialOct",
        "FinancialNov",
    }:
        start_month = {
            "FinancialApril": 4,
            "FinancialJuly": 7,
            "FinancialSep": 9,
            "FinancialOct": 10,
            "FinancialNov": 11,
        }[period_type]
        start_year = d.year if d.month >= start_month else d.year - 1
        suffix = period_type.replace("Financial", "")
        return f"{start_year}{suffix}"

    raise ValueError(f"Formatting not implemented for period type '{period_type}'")
