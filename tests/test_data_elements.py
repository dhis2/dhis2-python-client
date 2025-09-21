import httpx
import pytest

from dhis2_client import DHIS2Client

BASE = "http://test"


@pytest.mark.unit
def test_list_data_elements(respx_mock):
    respx_mock.get(f"{BASE}/api/dataElements").mock(
        return_value=httpx.Response(
            200,
            json={
                "dataElements": [{"id": "de1", "displayName": "DE"}],
                "pager": {"page": 1, "pageCount": 1},
            },
        )
    )
    c = DHIS2Client(BASE)
    items = list(c.get_data_elements(fields="id,displayName"))
    assert items and items[0]["id"] == "de1"


@pytest.mark.unit
def test_de_crud(respx_mock):
    respx_mock.get(f"{BASE}/api/dataElements/de1").mock(
        return_value=httpx.Response(200, json={"id": "de1"})
    )
    respx_mock.post(f"{BASE}/api/dataElements").mock(
        return_value=httpx.Response(200, json={"response": {"status": "OK"}})
    )
    respx_mock.put(f"{BASE}/api/dataElements/de1").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    respx_mock.delete(f"{BASE}/api/dataElements/de1").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    c = DHIS2Client(BASE)
    assert c.get_data_element("de1")["id"] == "de1"
    assert c.create_data_element({"name": "X"})["response"]["status"] in {"OK", "SUCCESS"}
    assert c.update_data_element("de1", {"name": "Y"})["status"] == "OK"
    assert c.delete_data_element("de1")["status"] == "OK"
