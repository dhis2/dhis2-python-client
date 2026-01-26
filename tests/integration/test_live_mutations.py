import os
from datetime import date
import pytest

from dhis2_client.errors import DHIS2HTTPError

pytestmark = pytest.mark.integration

ALLOW = os.environ.get("DHIS2_ALLOW_MUTATIONS", "").lower() in {"1", "true", "yes"}

OU_CHILD = os.environ.get("TEST_OU_CHILD")  # optional override
DE_A = os.environ.get("TEST_DE_A")          # optional override
DS_ID = os.environ.get("TEST_DS_ID")        # optional override


def last_closed_month_yyyymm(today: date | None = None) -> str:
    if today is None:
        today = date.today()
    y, m = today.year, today.month - 1
    if m == 0:
        y -= 1
        m = 12
    return f"{y}{m:02d}"


PERIOD = os.environ.get("TEST_PERIOD") or last_closed_month_yyyymm()


def _resolve_default_coc_id(c) -> str:
    coc = c.get("/api/categoryOptionCombos", params={"fields": "id,name", "filter": "name:eq:default", "pageSize": 1})
    items = coc.get("categoryOptionCombos") or []
    if not items:
        raise AssertionError("Could not resolve default CategoryOptionCombo; check your instance.")
    return items[0]["id"]


def _discover_monthly_ds_ou_de(c):
    """
    Find a Monthly dataset with at least:
      - one organisationUnit
      - one dataSetElement.dataElement
    Returns (ds_id, ou_id, de_id).
    """
    r = c.get(
        "/api/dataSets",
        params={
            "fields": "id,periodType,organisationUnits[id],dataSetElements[dataElement[id]]",
            "pageSize": 50,
        },
    )
    for ds in (r.get("dataSets") or []):
        if ds.get("periodType") != "Monthly":
            continue
        ous = ds.get("organisationUnits") or []
        dses = ds.get("dataSetElements") or []
        if not ous or not dses:
            continue
        ou_id = ous[0].get("id")
        de = dses[0].get("dataElement") or {}
        de_id = de.get("id")
        if ou_id and de_id:
            return ds["id"], ou_id, de_id
    return None


@pytest.mark.skipif(not ALLOW, reason="Mutations disabled (set DHIS2_ALLOW_MUTATIONS=true)")
def test_datavalue_roundtrip_and_dvs(live_client):
    c = live_client

    default_coc = _resolve_default_coc_id(c)

    ds_id, ou_id, de_id = DS_ID, OU_CHILD, DE_A
    if not (ds_id and ou_id and de_id):
        found = _discover_monthly_ds_ou_de(c)
        if not found:
            pytest.skip("No suitable Monthly dataset found (with OU + DE). Set TEST_DS_ID/TEST_OU_CHILD/TEST_DE_A.")
        ds_id, ou_id, de_id = found

    payload = {
        "dataSet": ds_id,
        "orgUnit": ou_id,
        "period": PERIOD,
        "dataValues": [{"dataElement": de_id, "categoryOptionCombo": default_coc, "value": "7"}],
    }

    try:
        resp = c.post_data_value_set(payload)
    except DHIS2HTTPError as e:
        raise AssertionError(f"DVS import failed: status={e.status_code}, path={e.path}, payload={e.payload}") from e

    assert resp is not None  # success shapes vary by DHIS2

    got = c.get_data_value(de=de_id, pe=PERIOD, ou=ou_id, co=default_coc)
    val = None
    if isinstance(got, dict):
        val = got.get("value")
    elif isinstance(got, list):
        if got:
            first = got[0]
            if isinstance(first, dict):
                val = first.get("value")
            else:
                val = first

    if isinstance(val, list):
        val = val[0] if val else None

    assert val == "7", f"Expected value '7', got {got!r}"



    _ = c.delete_data_value(de=de_id, pe=PERIOD, ou=ou_id, co=default_coc)
