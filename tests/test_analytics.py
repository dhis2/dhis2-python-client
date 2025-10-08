import httpx
import pytest

from dhis2_client import DHIS2Client

BASE = "http://test"


def _mock_de_monthly(respx_mock, de_uid="fbfJHSPpUQD"):
    respx_mock.get(f"{BASE}/api/dataElements/{de_uid}.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "dataSetElements": [
                    {"dataSet": {"id": "DSA", "name": "Monthly DS", "periodType": "MONTHLY"}}
                ]
            },
        )
    )


def _mock_ous_level(respx_mock, ids):
    respx_mock.get(f"{BASE}/api/organisationUnits").mock(
        return_value=httpx.Response(
            200, json={"organisationUnits": [{"id": i} for i in ids]}
        )
    )


def _mock_system_calendar(respx_mock, calendar="iso8601"):
    respx_mock.get(f"{BASE}/api/system/info").mock(
        return_value=httpx.Response(200, json={"calendar": calendar})
    )



@pytest.mark.unit
def test_get_analytics(respx_mock):
    respx_mock.get(f"{BASE}/api/analytics").mock(
        return_value=httpx.Response(
            200,
            json={
                "headers": [{"name": "dx"}, {"name": "pe"}],
                "rows": [["de1", "202401"], ["de2", "202401"]],
            },
        )
    )
    c = DHIS2Client(BASE)
    resp = c.get_analytics(dimension=["dx:de1;de2", "pe:202401"], skipMeta=True)
    assert "headers" in resp and "rows" in resp


@pytest.mark.unit
def test_latest_period_for_level_monthly_happy_path(respx_mock):
    """
    - iso8601 calendar
    - DE Monthly
    - Level-2 has two OUs
    - Current-year window returns periods up to 202510
    Expect:
      existing.id == 202510
      next.id == 202511
      years_checked == 1
    """
    _mock_system_calendar(respx_mock, "iso8601")
    _mock_de_monthly(respx_mock, "fbfJHSPpUQD")
    _mock_ous_level(respx_mock, ["OU1", "OU2"])

    # Any start/end; we just need the payload to include period codes
    respx_mock.get(f"{BASE}/api/dataValueSets").mock(
        return_value=httpx.Response(
            200,
            json={
                "dataValues": [
                    {"dataElement": "fbfJHSPpUQD", "orgUnit": "OU1", "period": "202501", "value": "1"},
                    {"dataElement": "fbfJHSPpUQD", "orgUnit": "OU2", "period": "202510", "value": "2"},
                ]
            },
        )
    )

    c = DHIS2Client(BASE)
    resp = c.analytics_latest_period_for_level(de_uid="fbfJHSPpUQD", level=2)

    assert resp["meta"]["periodType"] == "MONTHLY"
    assert resp["meta"]["calendar"] == "iso8601"
    assert resp["meta"]["years_checked"] == 1
    assert resp["existing"]["id"] == "202510"
    assert resp["next"]["id"] == "202511"
    assert resp["existing"]["startDate"] == "2025-10-01"
    assert resp["existing"]["endDate"] == "2025-10-31"


@pytest.mark.unit
def test_latest_period_for_level_falls_back_to_previous_year(respx_mock):
    """
    - First dataValueSets (current-year) returns empty -> no periods
    - Second call (previous year) returns data up to 202312
    Expect:
      existing.id == 202312
      next.id == 202401
      years_checked == 2  (current + previous)
    """
    _mock_system_calendar(respx_mock, "iso8601")
    _mock_de_monthly(respx_mock, "DEMONTH")
    _mock_ous_level(respx_mock, ["OUA", "OUB"])

    # We need two sequential responses for /api/dataValueSets:
    # 1) empty (current year)
    # 2) has data (previous year)
    route = respx_mock.get(f"{BASE}/api/dataValueSets")
    route.side_effect = [
        httpx.Response(200, json={"dataValues": []}),
        httpx.Response(
            200,
            json={
                "dataValues": [
                    {"dataElement": "DEMONTH", "orgUnit": "OUA", "period": "202311", "value": "7"},
                    {"dataElement": "DEMONTH", "orgUnit": "OUB", "period": "202312", "value": "9"},
                ]
            },
        ),
    ]

    c = DHIS2Client(BASE)
    resp = c.analytics_latest_period_for_level(de_uid="DEMONTH", level=3)

    assert resp["existing"]["id"] == "202312"
    assert resp["next"]["id"] == "202401"
    assert resp["meta"]["years_checked"] == 2


@pytest.mark.unit
def test_latest_period_for_level_mixed_dataset_frequencies_raises(respx_mock):
    """
    - DE linked to MONTHLY and QUARTERLY datasets → should raise ValueError
    """
    _mock_system_calendar(respx_mock, "iso8601")
    # Mixed frequencies
    respx_mock.get(f"{BASE}/api/dataElements/DE_MIXED.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "dataSetElements": [
                    {"dataSet": {"id": "DSM", "name": "Monthly", "periodType": "MONTHLY"}},
                    {"dataSet": {"id": "DSQ", "name": "Quarterly", "periodType": "QUARTERLY"}},
                ]
            },
        )
    )
    _mock_ous_level(respx_mock, ["OU1"])

    c = DHIS2Client(BASE)
    with pytest.raises(ValueError):
        c.analytics_latest_period_for_level(de_uid="DE_MIXED", level=2)


@pytest.mark.unit
def test_latest_period_for_level_no_ous(respx_mock):
    """
    - Level returns no organisationUnits → existing/next None, years_checked=0
    """
    _mock_system_calendar(respx_mock, "iso8601")
    _mock_de_monthly(respx_mock, "DEEMPTY")
    respx_mock.get(f"{BASE}/api/organisationUnits").mock(
        return_value=httpx.Response(200, json={"organisationUnits": []})
    )

    c = DHIS2Client(BASE)
    resp = c.analytics_latest_period_for_level(de_uid="DEEMPTY", level=9)

    assert resp["existing"] is None and resp["next"] is None
    assert resp["meta"]["years_checked"] == 0