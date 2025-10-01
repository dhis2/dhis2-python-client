import httpx
import pytest

from dhis2_client import DHIS2Client

BASE = "http://test"
JSON_PATCH = "application/json-patch+json"


@pytest.mark.unit
def test_add_user_org_unit_scopes_dedupe_and_header(respx_mock):
    uid = "U123"

    # Current scopes: capture has A, others empty
    respx_mock.get(f"{BASE}/api/users/{uid}").mock(
        return_value=httpx.Response(
            200,
            json={
                "organisationUnits": [{"id": "A"}],
                "dataViewOrganisationUnits": [],
                "teiSearchOrganisationUnits": [],
            },
        )
    )

    def patch_user(req: httpx.Request) -> httpx.Response:
        assert req.headers.get("Content-Type") == JSON_PATCH
        # We add capture=["A","B"] and view=["V1"]; dedupe removes A
        assert req.json() == [
            {"op": "add", "path": "/organisationUnits/-", "value": {"id": "B"}},
            {"op": "add", "path": "/dataViewOrganisationUnits/-", "value": {"id": "V1"}},
        ]
        return httpx.Response(200, json={"httpStatus": "OK"})

    respx_mock.patch(f"{BASE}/api/users/{uid}").mock(side_effect=patch_user)

    c = DHIS2Client(base_url=BASE)
    out = c.add_user_org_unit_scopes(uid, capture=["A", "B"], view=["V1"])
    assert out["httpStatus"] == "OK"


@pytest.mark.unit
def test_replace_user_org_unit_scopes_capture_only(respx_mock):
    uid = "U456"

    def patch_user(req: httpx.Request) -> httpx.Response:
        assert req.headers.get("Content-Type") == JSON_PATCH
        assert req.json() == [
            {"op": "replace", "path": "/organisationUnits", "value": [{"id": "X"}, {"id": "Y"}]}
        ]
        return httpx.Response(200, json={"httpStatus": "OK"})

    respx_mock.patch(f"{BASE}/api/users/{uid}").mock(side_effect=patch_user)

    c = DHIS2Client(base_url=BASE)
    out = c.replace_user_org_unit_scopes(uid, capture=["X", "Y"])
    assert out["httpStatus"] == "OK"


@pytest.mark.unit
def test_remove_user_org_unit_scopes_read_filter_replace(respx_mock):
    uid = "U789"
    # initial arrays
    respx_mock.get(f"{BASE}/api/users/{uid}").mock(
        return_value=httpx.Response(
            200,
            json={
                "organisationUnits": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
                "dataViewOrganisationUnits": [{"id": "V1"}],
                "teiSearchOrganisationUnits": [{"id": "T1"}, {"id": "T2"}],
            },
        )
    )

    def patch_user(req: httpx.Request) -> httpx.Response:
        assert req.headers.get("Content-Type") == JSON_PATCH
        # remove capture=["B"], tei=["T2"]; view untouched
        assert req.json() == [
            {"op": "replace", "path": "/organisationUnits", "value": [{"id": "A"}, {"id": "C"}]},
            {"op": "replace", "path": "/teiSearchOrganisationUnits", "value": [{"id": "T1"}]},
        ]
        return httpx.Response(200, json={"httpStatus": "OK"})

    respx_mock.patch(f"{BASE}/api/users/{uid}").mock(side_effect=patch_user)

    c = DHIS2Client(base_url=BASE)
    out = c.remove_user_org_unit_scopes(uid, capture=["B"], tei=["T2"])
    assert out["httpStatus"] == "OK"


@pytest.mark.unit
def test_add_my_org_unit_scopes_uses_api_me(respx_mock):
    # Resolve /api/me
    respx_mock.get(f"{BASE}/api/me").mock(return_value=httpx.Response(200, json={"id": "Ume"}))
    # My current scopes: none
    respx_mock.get(f"{BASE}/api/users/Ume").mock(
        return_value=httpx.Response(
            200,
            json={"organisationUnits": [], "dataViewOrganisationUnits": [], "teiSearchOrganisationUnits": []},
        )
    )

    def patch_me(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/users/Ume"
        assert req.headers.get("Content-Type") == JSON_PATCH
        assert req.json() == [
            {"op": "add", "path": "/organisationUnits/-", "value": {"id": "A"}},
            {"op": "add", "path": "/teiSearchOrganisationUnits/-", "value": {"id": "T1"}},
        ]
        return httpx.Response(200, json={"httpStatus": "OK"})

    respx_mock.patch(f"{BASE}/api/users/Ume").mock(side_effect=patch_me)

    c = DHIS2Client(base_url=BASE)
    out = c.add_my_org_unit_scopes(capture=["A"], tei=["T1"])
    assert out["httpStatus"] == "OK"
