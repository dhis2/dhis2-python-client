from datetime import date

import pytest
from dhis2_client.models import DataSet, format_period, validate_period
from pydantic import ValidationError


def test_validate_period_happy_paths():
    validate_period("Daily", "20250101")
    validate_period("Monthly", "202501")
    validate_period("Quarterly", "2025Q4")
    validate_period("SixMonthly", "2025S2")
    validate_period("Yearly", "2025")
    validate_period("Weekly", "2025W01")
    validate_period("BiMonthly", "202501B")


def test_validate_period_bad_inputs():
    with pytest.raises(ValueError):
        validate_period("Daily", "2025-01-01")
    with pytest.raises(ValueError):
        validate_period("Monthly", "2025M01")
    with pytest.raises(ValueError):
        validate_period("Quarterly", "2025Q5")


def test_format_period_common():
    d = date(2025, 1, 15)
    assert format_period("Daily", d) == "20250115"
    assert format_period("Monthly", d) == "202501"
    assert format_period("Quarterly", d) == "2025Q1"
    assert format_period("SixMonthly", d) == "2025S1"
    assert format_period("Yearly", d) == "2025"
    assert format_period("Weekly", d) == "2025W03"


def test_format_period_bimonthly_quarterlynov():
    d = date(2025, 2, 10)
    assert format_period("BiMonthly", d) == "202501B"
    assert format_period("QuarterlyNov", d) == "2024NovQ2"


def test_dataset_period_type_model_validation():
    DataSet(name="Demo", periodType="Monthly")
    with pytest.raises(ValidationError):
        DataSet(name="Demo", periodType="Nope")
