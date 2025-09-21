import json

import httpx
import pytest

from dhis2_client import DHIS2Client, DHIS2HTTPError

BASE = "http://test"


def _req_json(route_call) -> dict:
    """Decode JSON body from a recorded respx call."""
    body = route_call.request.content  # bytes
    return json.loads(body.decode() or "{}")


@pytest.mark.unit
def test_get_data_value_builds_params(respx_mock):
    respx_mock.get(f"{BASE}/api/dataValues").mock(
        return_value=httpx.Response(200, json={"value": "42"})
    )
    c = DHIS2Client(base_url=BASE)

    got = c.get_data_value(de="de1", pe="202401", ou="ou1", co="co1")
    assert got["value"] == "42"

    r = respx_mock.calls[-1].request  # last call
    qs = dict(httpx.QueryParams(r.url.query))
    assert qs == {"de": "de1", "pe": "202401", "ou": "ou1", "co": "co1"}


@pytest.mark.unit
def test_set_data_value_posts_payload(respx_mock):
    route = respx_mock.post(f"{BASE}/api/dataValues").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    c = DHIS2Client(base_url=BASE)

    resp = c.set_data_value(de="de1", pe="202401", ou="ou1", co="co1", value="7")
    assert resp["status"] == "OK"

    sent = _req_json(route.calls.last)
    assert sent == {
        "dataElement": "de1",
        "period": "202401",
        "orgUnit": "ou1",
        "categoryOptionCombo": "co1",
        "value": "7",
    }


@pytest.mark.unit
def test_delete_data_value_uses_querystring(respx_mock):
    route = respx_mock.delete(f"{BASE}/api/dataValues").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    c = DHIS2Client(base_url=BASE)

    resp = c.delete_data_value(de="de1", pe="202401", ou="ou1", co="co1")
    assert resp["status"] == "OK"

    r = route.calls.last.request
    qs = dict(httpx.QueryParams(r.url.query))
    assert qs == {"de": "de1", "pe": "202401", "ou": "ou1", "co": "co1"}


@pytest.mark.unit
def test_get_data_value_set_passes_params(respx_mock):
    route = respx_mock.get(f"{BASE}/api/dataValueSets").mock(
        return_value=httpx.Response(200, json={"dataValues": []})
    )
    c = DHIS2Client(base_url=BASE)

    params = {"dataSet": "ds1", "period": "202401", "orgUnit": "ou1"}
    got = c.get_data_value_set(params)
    assert got["dataValues"] == []

    r = route.calls.last.request
    qs = dict(httpx.QueryParams(r.url.query))
    assert qs == params


@pytest.mark.unit
def test_post_data_value_set_posts_payload(respx_mock, fx):
    # Uses tests/fixtures/data_value_set.json
    payload = fx.json("data_value_set.json")

    route = respx_mock.post(f"{BASE}/api/dataValueSets").mock(
        return_value=httpx.Response(200, json={"status": "SUCCESS", "importCount": {"imported": 2}})
    )
    c = DHIS2Client(base_url=BASE)

    got = c.post_data_value_set(payload)
    assert got["status"] in {"SUCCESS", "OK"}

    sent = _req_json(route.calls.last)
    assert sent == payload


@pytest.mark.unit
def test_post_data_value_set_raises_on_conflict(respx_mock):
    conflict_body = {
        "httpStatus": "Conflict",
        "response": {
            "status": "ERROR",
            "conflicts": [{"object": "dataElement", "value": "Invalid UID"}],
        },
    }
    respx_mock.post(f"{BASE}/api/dataValueSets").mock(
        return_value=httpx.Response(409, json=conflict_body)
    )
    c = DHIS2Client(base_url=BASE)

    with pytest.raises(DHIS2HTTPError) as ei:
        c.post_data_value_set(
            {"dataSet": "ds1", "orgUnit": "ou1", "period": "202401", "dataValues": []}
        )

    err = ei.value
    assert err.status_code == 409
    assert err.payload["response"]["status"] == "ERROR"
