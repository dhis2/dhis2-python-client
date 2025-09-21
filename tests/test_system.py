import httpx
import pytest

from dhis2_client import DHIS2Client

BASE = "http://test"


@pytest.mark.unit
def test_get_system_info(respx_mock):
    respx_mock.get(f"{BASE}/api/system/info").mock(
        return_value=httpx.Response(200, json={"version": "2.41.0", "systemName": "DHIS2"})
    )
    c = DHIS2Client(BASE)
    info = c.get_system_info()
    assert info["version"] == "2.41.0"
    assert "systemName" in info
