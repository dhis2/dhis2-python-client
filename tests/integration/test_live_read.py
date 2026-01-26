import os
import pytest

pytestmark = pytest.mark.integration

OU_CHILD = os.environ.get("TEST_OU_CHILD")  # optional
DS_ID = os.environ.get("TEST_DS_ID")        # optional


def _first_id(resp: dict, key: str) -> str | None:
    items = resp.get(key) or []
    if items and isinstance(items[0], dict):
        return items[0].get("id")
    return None


def test_system_info_and_reads(live_client):
    c = live_client

    info = c.get_system_info()
    assert "version" in info

    # users (just ensure it works)
    _ = list(c.get_users(fields="id,username", pageSize=3))

    # org unit: use TEST_OU_CHILD if supplied, else pick first level-1 OU if any
    ou_id = OU_CHILD
    if not ou_id:
        r = c.get("/api/organisationUnits", params={"fields": "id", "pageSize": 1})
        ou_id = _first_id(r, "organisationUnits")
    if ou_id:
        ou = c.get_org_unit(ou_id, fields="id,displayName")
        assert ou.get("id") == ou_id

    # dataset: use TEST_DS_ID if supplied, else pick first dataset if any
    ds_id = DS_ID
    if not ds_id:
        r = c.get("/api/dataSets", params={"fields": "id", "pageSize": 1})
        ds_id = _first_id(r, "dataSets")
    if ds_id:
        ds = c.get_data_set(ds_id, fields="id,displayName,periodType")
        assert ds.get("id") == ds_id
