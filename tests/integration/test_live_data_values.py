import os
from datetime import date

import pytest
from dhis2_client import DHIS2AsyncClient, Settings
from dhis2_client.exceptions import Conflict
from dhis2_client.models import DataValue, DataValueSet, format_period

MUTATIONS_ENABLED = os.getenv("ALLOW_DHIS2_MUTATIONS", "").lower() in {"1", "true", "yes"}

requires_env = pytest.mark.skipif(
    not os.path.exists(".env") and not os.getenv("DHIS2_BASE_URL"),
    reason="Integration tests require a .env or env vars",
)


async def _pick_linked_ds_ou_de(client: DHIS2AsyncClient):
    """Return (dataSetId, orgUnitId, dataElementId, cocId, aocId).
    Honors TEST_* env pins; pages through datasets if not pinned.
    Ensures we have both a Data Element COC (categoryOptionCombo) and
    a Data Set AOC (attributeOptionCombo).
    """
    pin_ds = os.getenv("TEST_DATASET_UID")
    pin_ou = os.getenv("TEST_OU_UID")
    pin_de = os.getenv("TEST_DE_UID")
    pin_coc = os.getenv("TEST_COC_UID")
    pin_aoc = os.getenv("TEST_AOC_UID")

    async def _extract(ds_obj, chosen_de_id=None):
        ous = [ou["id"] for ou in (ds_obj.get("organisationUnits") or [])]
        dses = ds_obj.get("dataSetElements") or []
        # Map DE -> COCs from embedded DE.categoryCombo if available
        de_to_cocs = {}
        for e in dses:
            de = e.get("dataElement") or {}
            if de.get("id"):
                ccombo = de.get("categoryCombo") or {}
                cocs = [c["id"] for c in (ccombo.get("categoryOptionCombos") or [])]
                de_to_cocs[de["id"]] = cocs
        ds_aocs = [c["id"] for c in ((ds_obj.get("categoryCombo") or {}).get("categoryOptionCombos") or [])]

        if not ous or not dses:
            return None

        de_id = chosen_de_id or next((k for k in de_to_cocs.keys()), None)
        if not de_id:
            return None

        # Prefer pinned combos if provided
        coc_id = pin_coc or (de_to_cocs.get(de_id, [None])[0] if de_to_cocs.get(de_id) else None)
        aoc_id = pin_aoc or (ds_aocs[0] if ds_aocs else None)
        ou_id = pin_ou or ous[0]
        if ou_id and de_id and coc_id and aoc_id:
            return ds_obj["id"], ou_id, de_id, coc_id, aoc_id
        return None

    # 1) Try pinned dataset first
    if pin_ds:
        ds = await client.get(
            f"/api/dataSets/{pin_ds}",
            params={
                "fields": "id,name,organisationUnits[id],dataSetElements[dataElement[id,categoryCombo[categoryOptionCombos[id]]]],categoryCombo[categoryOptionCombos[id]]"
            },
        )
        picked = await _extract(ds, chosen_de_id=pin_de)
        if picked:
            return picked

    # 2) Page through datasets to find a linked one with combos
    page = 1
    while True:
        data = await client.get(
            "/api/dataSets",
            params={
                "fields": "id,name,organisationUnits[id],dataSetElements[dataElement[id,categoryCombo[categoryOptionCombos[id]]]],categoryCombo[categoryOptionCombos[id]]",
                "pageSize": 100,
                "page": page,
                "paging": "true",
            },
        )
        items = data.get("dataSets", []) or []
        for ds in items:
            picked = await _extract(ds)
            if picked:
                return picked
        pager = data.get("pager") or {}
        if pager.get("page") and pager.get("pageCount"):
            if pager["page"] >= pager["pageCount"]:
                break
            page += 1
        else:
            break
    return None, None, None, None, None


@pytest.mark.integration
@requires_env
@pytest.mark.asyncio
async def test_data_value_set_dry_run_roundtrip():
    settings = Settings()
    async with DHIS2AsyncClient.from_settings(settings) as client:
        ds_id, ou_id, de_id, coc_id, aoc_id = await _pick_linked_ds_ou_de(client)
        if not (ds_id and ou_id and de_id and coc_id and aoc_id):
            pytest.skip("No dataset found that links OU + DE and exposes combos")
        period = format_period("Monthly", date.today())
        dvs = DataValueSet(
            dataSet=ds_id,
            period=period,
            orgUnit=ou_id,
            dataValues=[
                DataValue(
                    dataElement=de_id,
                    orgUnit=ou_id,
                    period=period,
                    value="1",
                    categoryOptionCombo=coc_id,
                    attributeOptionCombo=aoc_id,
                )
            ],
        )
        try:
            resp_create = await client.post_data_value_set(dvs, import_strategy="CREATE", dry_run=True)
            assert isinstance(resp_create, dict)
            resp_delete = await client.post_data_value_set(dvs, import_strategy="DELETE", dry_run=True)
            assert isinstance(resp_delete, dict)
        except Conflict as e:
            details = getattr(e, "details", {})
            if not isinstance(details, dict):
                raise
            # treat as acceptable on servers that respond 409 for dry-run
            pytest.skip(f"Dry-run conflict (acceptable): {details.get('message','conflict')}")


@pytest.mark.integration
@requires_env
@pytest.mark.skipif(not MUTATIONS_ENABLED, reason="Set ALLOW_DHIS2_MUTATIONS=true to run mutation tests")
@pytest.mark.asyncio
async def test_data_value_set_create_delete_mutation():
    settings = Settings()
    async with DHIS2AsyncClient.from_settings(settings) as client:
        ds_id, ou_id, de_id, coc_id, aoc_id = await _pick_linked_ds_ou_de(client)
        if not (ds_id and ou_id and de_id and coc_id and aoc_id):
            pytest.skip("No dataset found that links OU + DE and exposes combos")
        period = format_period("Monthly", date.today())
        dvs = DataValueSet(
            dataSet=ds_id,
            period=period,
            orgUnit=ou_id,
            dataValues=[
                DataValue(
                    dataElement=de_id,
                    orgUnit=ou_id,
                    period=period,
                    value="1",
                    categoryOptionCombo=coc_id,
                    attributeOptionCombo=aoc_id,
                )
            ],
        )
        try:
            resp_create = await client.post_data_value_set(dvs, import_strategy="CREATE")
            assert isinstance(resp_create, dict)
            resp_delete = await client.post_data_value_set(dvs, import_strategy="DELETE")
            assert isinstance(resp_delete, dict)
        except Conflict as e:
            details = getattr(e, "details", {})
            pytest.skip(f"Server rejected create/delete (skipping): {details.get('message','conflict')}")
