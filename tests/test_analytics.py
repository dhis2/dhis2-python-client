import httpx
import pytest

from dhis2_client import DHIS2Client

BASE = "http://test"


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
