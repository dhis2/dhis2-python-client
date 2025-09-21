import httpx
import pytest

from dhis2_client import DHIS2Client

BASE = "http://test"


@pytest.mark.unit
def test_get_users_list(respx_mock):
    respx_mock.get(f"{BASE}/api/users").mock(
        return_value=httpx.Response(
            200,
            json={
                "users": [
                    {"id": "u1", "username": "alpha"},
                    {"id": "u2", "username": "beta"},
                ],
                "pager": {"page": 1, "pageCount": 1, "total": 2},
            },
        )
    )
    c = DHIS2Client(base_url=BASE)
    got = list(c.get_users(fields="id,username", pageSize=50))
    assert len(got) == 2
    assert got[0]["id"] == "u1"


@pytest.mark.unit
def test_get_user_by_id(respx_mock):
    respx_mock.get(f"{BASE}/api/users/u1").mock(
        return_value=httpx.Response(200, json={"id": "u1", "username": "alpha"})
    )
    c = DHIS2Client(base_url=BASE)
    got = c.get_user("u1", fields="id,username")
    assert got["id"] == "u1"
