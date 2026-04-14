from dhis2_client.utils.calendar import period_key, next_period_id, period_start_end

def test_period_key_and_next_monthly():
    assert period_key("202512") > period_key("202511")
    assert next_period_id("202512") == "202601"
    se = period_start_end("202502")
    assert se["startDate"] == "2025-02-01"
    assert se["endDate"] == "2025-02-28" or se["endDate"] == "2025-02-29"

def test_period_key_and_next_quarterly():
    assert period_key("2024Q4") > period_key("2024Q3")
    assert next_period_id("2024Q4") == "2025Q1"
    se = period_start_end("2024Q2")
    assert se["startDate"] == "2024-04-01"
    assert se["endDate"] == "2024-06-30"

def test_period_key_and_next_yearly():
    assert period_key("2025") > period_key("2024")
    assert next_period_id("2025") == "2026"
    se = period_start_end("2025")
    assert se["startDate"] == "2025-01-01"
    assert se["endDate"] == "2025-12-31"


def test_period_key_and_next_daily():
    assert period_key("20250102") > period_key("20250101")
    assert next_period_id("20250131") == "20250201"


def test_period_key_and_next_weekly():
    assert period_key("2025W02") > period_key("2025W01")
    assert next_period_id("2025W52") == "2026W01"


def test_period_key_and_next_six_monthly():
    assert period_key("2025S2") > period_key("2025S1")
    assert next_period_id("2025S2") == "2026S1"


def test_period_key_supports_date_ranges():
    assert period_key("20250101_20250131") > period_key("20241201_20241231")
