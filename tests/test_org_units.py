import httpx
import pytest

from dhis2_client import DHIS2Client, DHIS2HTTPError

BASE = "http://test"


@pytest.mark.unit
def test_list_org_units(respx_mock):
    respx_mock.get(f"{BASE}/api/organisationUnits").mock(
        return_value=httpx.Response(
            200,
            json={
                "organisationUnits": [{"id": "ou1", "displayName": "A"}],
                "pager": {"page": 1, "pageCount": 1, "total": 1},
            },
        )
    )
    c = DHIS2Client(BASE)
    items = list(c.get_organisation_units(fields="id,displayName", level=2))
    assert items and items[0]["id"] == "ou1"


@pytest.mark.unit
def test_get_org_unit(respx_mock):
    respx_mock.get(f"{BASE}/api/organisationUnits/ou1").mock(
        return_value=httpx.Response(200, json={"id": "ou1", "displayName": "A"})
    )
    c = DHIS2Client(BASE)
    got = c.get_org_unit("ou1", fields="id,displayName")
    assert got["id"] == "ou1"


@pytest.mark.unit
def test_create_org_unit(respx_mock):
    respx_mock.post(f"{BASE}/api/organisationUnits").mock(
        return_value=httpx.Response(200, json={"response": {"status": "OK", "uid": "ouX"}})
    )
    c = DHIS2Client(BASE)
    payload = {"name": "New OU", "shortName": "NOU", "openingDate": "2020-01-01"}
    resp = c.create_org_unit(payload)
    assert resp["response"]["status"] in {"OK", "SUCCESS"}


@pytest.mark.unit
def test_update_org_unit(respx_mock):
    respx_mock.put(f"{BASE}/api/organisationUnits/ou1").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    c = DHIS2Client(BASE)
    resp = c.update_org_unit("ou1", {"name": "Renamed"})
    assert resp["status"] == "OK"


@pytest.mark.unit
def test_delete_org_unit(respx_mock):
    respx_mock.delete(f"{BASE}/api/organisationUnits/ou1").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    c = DHIS2Client(BASE)
    resp = c.delete_org_unit("ou1")
    assert resp["status"] == "OK"


@pytest.mark.unit
def test_org_unit_conflict_raises(respx_mock):
    respx_mock.post(f"{BASE}/api/organisationUnits").mock(
        return_value=httpx.Response(
            409,
            json={
                "httpStatus": "Conflict",
                "response": {
                    "status": "ERROR",
                    "conflicts": [{"object": "name", "value": "Already exists"}],
                },
            },
        )
    )
    c = DHIS2Client(BASE)
    try:
        c.create_org_unit({"name": "Dup", "shortName": "Dup"})
        assert False, "Expected DHIS2HTTPError"
    except DHIS2HTTPError as e:
        assert e.status_code == 409
        assert e.payload["response"]["status"] == "ERROR"
