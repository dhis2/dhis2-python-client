import httpx
import pytest
import json

from dhis2_client import DHIS2Client

BASE = "http://test"


def _body(req: httpx.Request) -> dict:
    """
    Robustly parse JSON body from an httpx.Request across versions.
    """
    # In some httpx versions, .read() is needed to populate .content
    if hasattr(req, "read"):
        try:
            req.read()
        except Exception:
            pass
    raw = getattr(req, "content", b"") or b"{}"
    try:
        return json.loads(raw.decode("utf-8") or "{}")
    except Exception as e:
        raise AssertionError(f"Failed to parse request JSON: {e}; RAW={raw!r}") from e


@pytest.mark.unit
def test_grant_self_access_merges_current(respx_mock):
    # /api/me
    respx_mock.get(f"{BASE}/api/me").mock(return_value=httpx.Response(200, json={"id": "me123"}))
    # current sharing (metadata rw baseline + one user with DATA_READ)
    respx_mock.get(f"{BASE}/api/sharing").mock(
        return_value=httpx.Response(
            200,
            json={
                "object": {
                    "publicAccess": "rw-------",  # META_WRITE baseline
                    "userAccesses": [{"id": "u1", "access": "rwr-----"}],  # DATA_READ
                    "userGroupAccesses": [{"id": "g1", "access": "rw-------"}],  # meta rw
                }
            },
        )
    )

    def post_sharing(req: httpx.Request) -> httpx.Response:
        assert req.url.params.get("type") == "program"
        assert req.url.params.get("id") == "PrA"

        body = _body(req)
        assert "object" in body
        obj = body["object"]

        # public access unchanged
        assert obj["publicAccess"] == "rw-------"

        # merged users includes me123 at DATA_WRITE and keeps u1 at DATA_READ
        users = sorted(obj["userAccesses"], key=lambda x: x["id"])
        assert users == [
            {"id": "me123", "access": "rwrw----"},  # DATA_WRITE
            {"id": "u1", "access": "rwr-----"},     # DATA_READ
        ] or users == [
            {"id": "u1", "access": "rwr-----"},
            {"id": "me123", "access": "rwrw----"},
        ]

        # groups preserved
        assert obj["userGroupAccesses"] == [{"id": "g1", "access": "rw-------"}]
        return httpx.Response(200, json={"status": "OK"})

    respx_mock.post(f"{BASE}/api/sharing").mock(side_effect=post_sharing)

    c = DHIS2Client(base_url=BASE)
    out = c.grant_self_access(object_type="program", object_id="PrA", access="rwrw----")
    assert out["status"] == "OK"


@pytest.mark.unit
def test_set_public_access_keeps_users_groups(respx_mock):
    # current sharing (meta rw baseline)
    respx_mock.get(f"{BASE}/api/sharing").mock(
        return_value=httpx.Response(
            200,
            json={
                "object": {
                    "publicAccess": "rw-------",
                    "userAccesses": [{"id": "u1", "access": "rwr-----"}],  # DATA_READ
                    "userGroupAccesses": [{"id": "g1", "access": "rw-------"}],
                }
            },
        )
    )

    def post_sharing(req: httpx.Request) -> httpx.Response:
        assert req.url.params.get("type") == "dashboard"
        assert req.url.params.get("id") == "db1"

        body = _body(req)
        obj = body["object"]

        # publicAccess explicitly set to META_WRITE
        assert obj["publicAccess"] == "rw-------"
        # users/groups preserved
        assert obj["userAccesses"] == [{"id": "u1", "access": "rwr-----"}]
        assert obj["userGroupAccesses"] == [{"id": "g1", "access": "rw-------"}]
        return httpx.Response(200, json={"status": "OK"})

    respx_mock.post(f"{BASE}/api/sharing").mock(side_effect=post_sharing)

    c = DHIS2Client(base_url=BASE)
    out = c.set_public_access(object_type="dashboard", object_id="db1", public_access="rw-------")
    assert out["status"] == "OK"


@pytest.mark.unit
def test_grant_access_bulk_merge_and_public_toggle(respx_mock):
    # current sharing starts with meta rw public, one existing user/group at DATA_READ
    respx_mock.get(f"{BASE}/api/sharing").mock(
        return_value=httpx.Response(
            200,
            json={
                "object": {
                    "publicAccess": "rw-------",
                    "userAccesses": [{"id": "uOld", "access": "rwr-----"}],
                    "userGroupAccesses": [{"id": "gOld", "access": "rwr-----"}],
                }
            },
        )
    )

    def post_sharing(req: httpx.Request) -> httpx.Response:
        assert req.url.params.get("type") == "dataElement"
        assert req.url.params.get("id") == "deX"

        body = _body(req)
        obj = body["object"]

        # keep_public=False => remove public access
        assert obj["publicAccess"] == "--------"
        users = sorted(obj["userAccesses"], key=lambda x: x["id"])
        assert users == [
            {"id": "u1", "access": "rwrw----"},   # DATA_WRITE
            {"id": "u2", "access": "rwrw----"},   # DATA_WRITE
            {"id": "uOld", "access": "rwr-----"}, # DATA_READ
        ]
        groups = sorted(obj["userGroupAccesses"], key=lambda x: x["id"])
        assert groups == [
            {"id": "gEditors", "access": "rwrw----"},  # DATA_WRITE
            {"id": "gOld", "access": "rwr-----"},      # DATA_READ
        ]
        return httpx.Response(200, json={"status": "OK"})

    respx_mock.post(f"{BASE}/api/sharing").mock(side_effect=post_sharing)

    c = DHIS2Client(base_url=BASE)
    out = c.grant_access(
        object_type="dataElement",
        object_id="deX",
        user_ids=["u1", "u2"],
        user_group_ids=["gEditors"],
        access="rwrw----",   # DATA_WRITE
        keep_public=False,
    )
    assert out["status"] == "OK"


@pytest.mark.unit
def test_set_dataset_data_write_merges(respx_mock):
    # current dataset sharing (meta rw baseline, existing user/group at DATA_READ)
    respx_mock.get(f"{BASE}/api/sharing").mock(
        return_value=httpx.Response(
            200,
            json={
                "object": {
                    "publicAccess": "rw-------",
                    "userAccesses": [{"id": "uOld", "access": "rwr-----"}],
                    "userGroupAccesses": [{"id": "gOld", "access": "rwr-----"}],
                }
            },
        )
    )

    def post_sharing(req: httpx.Request) -> httpx.Response:
        assert req.url.params.get("type") == "dataSet"
        assert req.url.params.get("id") == "Ds1"

        body = _body(req)
        obj = body["object"]

        # publicAccess stays as given by call default (META_WRITE) unless overridden
        assert obj["publicAccess"] == "rw-------"
        users = sorted(obj["userAccesses"], key=lambda x: x["id"])
        assert users == [
            {"id": "u1", "access": "rwrw----"},   # DATA_WRITE
            {"id": "uOld", "access": "rwr-----"}, # DATA_READ (existing)
        ]
        groups = sorted(obj["userGroupAccesses"], key=lambda x: x["id"])
        assert groups == [
            {"id": "gEditors", "access": "rwrw----"},  # DATA_WRITE
            {"id": "gOld", "access": "rwr-----"},      # DATA_READ (existing)
        ]
        return httpx.Response(200, json={"status": "OK"})

    respx_mock.post(f"{BASE}/api/sharing").mock(side_effect=post_sharing)

    c = DHIS2Client(base_url=BASE)
    out = c.set_dataset_data_write("Ds1", user_ids=["u1"], user_group_ids=["gEditors"])
    assert out["status"] == "OK"
