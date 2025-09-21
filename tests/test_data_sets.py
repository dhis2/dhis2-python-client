import httpx
import pytest

from dhis2_client import DHIS2Client

BASE = "http://test"


@pytest.mark.unit
def test_list_data_sets(respx_mock):
    respx_mock.get(f"{BASE}/api/dataSets").mock(
        return_value=httpx.Response(
            200,
            json={
                "dataSets": [{"id": "ds1", "displayName": "DS"}],
                "pager": {"page": 1, "pageCount": 1},
            },
        )
    )
    c = DHIS2Client(BASE)
    items = list(c.get_data_sets(fields="id,displayName"))
    assert items and items[0]["id"] == "ds1"


@pytest.mark.unit
def test_ds_crud(respx_mock):
    respx_mock.get(f"{BASE}/api/dataSets/ds1").mock(
        return_value=httpx.Response(200, json={"id": "ds1"})
    )
    respx_mock.post(f"{BASE}/api/dataSets").mock(
        return_value=httpx.Response(200, json={"response": {"status": "OK"}})
    )
    respx_mock.put(f"{BASE}/api/dataSets/ds1").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    respx_mock.delete(f"{BASE}/api/dataSets/ds1").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    c = DHIS2Client(BASE)
    assert c.get_data_set("ds1")["id"] == "ds1"
    assert c.create_data_set({"name": "X"})["response"]["status"] in {"OK", "SUCCESS"}
    assert c.update_data_set("ds1", {"name": "Y"})["status"] == "OK"
    assert c.delete_data_set("ds1")["status"] == "OK"
