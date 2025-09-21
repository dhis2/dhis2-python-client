import os
from datetime import date

import pytest

from dhis2_client import DHIS2Client
from dhis2_client.errors import DHIS2HTTPError
from dhis2_client.settings import ClientSettings

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("DHIS2_BASE_URL")
USERNAME = os.environ.get("DHIS2_USERNAME")
PASSWORD = os.environ.get("DHIS2_PASSWORD")
TOKEN = os.environ.get("DHIS2_TOKEN")
ALLOW = os.environ.get("DHIS2_ALLOW_MUTATIONS", "").lower() in {"1", "true", "yes"}

OU_CHILD = os.environ.get("TEST_OU_CHILD", "OuChild0001")
DE_A = os.environ.get("TEST_DE_A", "DeElem00001")
DS_ID = os.environ.get("TEST_DS_ID", "DsMonth0001")


def last_closed_month_yyyymm(today: date | None = None) -> str:
    """Previous month in YYYYMM (closed for Monthly datasets)."""
    if today is None:
        today = date.today()
    y, m = today.year, today.month
    m -= 1
    if m == 0:
        y -= 1
        m = 12
    return f"{y}{m:02d}"


# Use explicit override if provided; else last closed month.
PERIOD = os.environ.get("TEST_PERIOD") or last_closed_month_yyyymm()


@pytest.mark.skipif(not BASE_URL, reason="DHIS2_BASE_URL not set")
@pytest.mark.skipif(not ALLOW, reason="Mutations disabled (set DHIS2_ALLOW_MUTATIONS=true)")
def test_datavalue_roundtrip_and_dvs():
    # ---- client ----
    cfg = ClientSettings(
        base_url=BASE_URL,
        username=USERNAME if not TOKEN else None,
        password=PASSWORD if not TOKEN else None,
        token=TOKEN,
        log_level="INFO",
        log_destination="stdout",
    )
    c = DHIS2Client(settings=cfg)

    # ---- resolve default COC ----
    coc = c.get(
        "/api/categoryOptionCombos",
        params={"fields": "id,name", "filter": "name:eq:default", "pageSize": 1},
    )
    assert (
        isinstance(coc, dict) and "categoryOptionCombos" in coc and coc["categoryOptionCombos"]
    ), "Could not resolve default CategoryOptionCombo; check your instance."
    DEFAULT_COC_ID = coc["categoryOptionCombos"][0]["id"]

    # ---- dataset must exist and be linked to DE & OU ----
    ds = c.get(
        f"/api/dataSets/{DS_ID}",
        params={
            "fields": "id,name,periodType,dataSetElements[dataElement[id]],organisationUnits[id]"
        },
    )
    assert isinstance(ds, dict) and ds.get("id") == DS_ID, f"DataSet {DS_ID} not found."
    ds_de_ids = {d["dataElement"]["id"] for d in ds.get("dataSetElements", [])}
    ds_ou_ids = {o["id"] for o in ds.get("organisationUnits", [])}
    assert DE_A in ds_de_ids, f"DataSet {DS_ID} is not linked to DataElement {DE_A}."
    assert OU_CHILD in ds_ou_ids, f"DataSet {DS_ID} is not linked to OrgUnit {OU_CHILD}."

    # ---- write via DataValueSet (strict) ----
    payload = {
        "dataSet": DS_ID,
        "orgUnit": OU_CHILD,
        "period": PERIOD,
        "dataValues": [
            {"dataElement": DE_A, "categoryOptionCombo": DEFAULT_COC_ID, "value": "7"},
        ],
    }

    try:
        resp = c.post_data_value_set(payload)
    except DHIS2HTTPError as e:
        raise AssertionError(
            f"DVS import failed: status={e.status_code}, path={e.path}, payload={e.payload}"
        ) from e

    # Accept a couple of well-known success shapes; otherwise fail.
    ok = False
    if isinstance(resp, dict):
        status = resp.get("status") or resp.get("response", {}).get("status")
        ok = (
            (status in {"OK", "SUCCESS"})
            or ("importCount" in resp)
            or ("response" in resp)
            or (resp == {})
        )
    elif isinstance(resp, list):
        ok = True
    assert ok, f"Unexpected DVS response shape/content: {resp!r}"

    # ---- read back via single DV GET (strict, but normalize shape) ----
    got = c.get_data_value(de=DE_A, pe=PERIOD, ou=OU_CHILD, co=DEFAULT_COC_ID)

    def _normalize_value(resp) -> str | None:
        if isinstance(resp, dict):
            return resp.get("value")
        if isinstance(resp, list):
            if not resp:
                return None
            first = resp[0]
            if isinstance(first, dict):
                return first.get("value")
            return str(first)
        return None

    val = _normalize_value(got)
    assert val == "7", f"Expected value '7', got {got!r}"

    # ---- delete via single DV DELETE (strict-ish) ----
    del_resp = c.delete_data_value(de=DE_A, pe=PERIOD, ou=OU_CHILD, co=DEFAULT_COC_ID)
    # Server returns empty JSON on delete; just assert we got a response without exception.
    assert del_resp is not None
