import os
import uuid
from typing import Optional

import pytest
import pytest_asyncio
from dhis2_client import DHIS2AsyncClient, Settings
from dhis2_client.exceptions import Conflict

# ---- Global guards ------------------------------------------------------------

MUTATIONS_ENABLED = os.getenv("ALLOW_DHIS2_MUTATIONS", "").lower() in {"1", "true", "yes"}


# ---- Basic skip guards used by tests -----------------------------------------


@pytest.fixture
def requires_env():
    """Skip if there is no .env and no DHIS2_* env vars at all."""
    if not (os.path.exists(".env") or os.getenv("DHIS2_BASE_URL")):
        pytest.skip("Integration tests require a .env or DHIS2_* env vars")


@pytest.fixture
def requires_mutations():
    """Skip if mutation tests are not explicitly allowed."""
    if not MUTATIONS_ENABLED:
        pytest.skip("Set ALLOW_DHIS2_MUTATIONS=true to run mutation tests")


# ---- Helpers -----------------------------------------------------------------


async def _create_and_extract_uid(
    client: DHIS2AsyncClient, resource: str, payload: dict, name_field: str = "name"
) -> str:
    """
    Create a resource via POST /api/{resource} and return its UID.
    If the server does not echo the uid, we search by name and return the first match.
    """
    resp = await client.post_json(f"/api/{resource}", payload)
    uid = None
    if isinstance(resp, dict):
        # Common shapes: {response:{uid:id}}, or just {id|uid}
        if "response" in resp and isinstance(resp["response"], dict):
            uid = resp["response"].get("uid") or resp["response"].get("id")
        uid = uid or resp.get("uid") or resp.get("id")
    if uid:
        return uid

    name = payload.get(name_field)
    search = await client.get(
        f"/api/{resource}",
        params={"fields": "id,name", "paging": "false", "filter": f"name:eq:{name}"},
    )
    plural_key = resource if resource.endswith("s") else resource + "s"
    items = search.get(plural_key, [])
    assert items, f"Created {resource} not found by name"
    return items[0]["id"]


async def _extract_uid_from_response_or_search(
    client: DHIS2AsyncClient, resource: str, payload: dict, name_field: str = "name"
) -> str:
    """Wrapper around _create_and_extract_uid for readability."""
    return await _create_and_extract_uid(client, resource, payload, name_field)


async def _link_de_to_ds(client: DHIS2AsyncClient, de_uid: str, ds_uid: str) -> None:
    """Best-effort linking of DataElement -> DataSet across DHIS2 variants."""
    # Preferred: POST /dataSets/{id}/dataSetElements
    try:
        await client.post_json(f"/api/dataSets/{ds_uid}/dataSetElements", {"dataElement": {"id": de_uid}})
        return
    except Exception:
        pass
    # Alternate: POST /dataSets/{ds}/dataElements/{de}
    try:
        await client.post_json(f"/api/dataSets/{ds_uid}/dataElements/{de_uid}", {})
        return
    except Exception:
        pass
    # Last resort: PUT merge on DataSet
    try:
        await client.put_json(
            f"/api/dataSets/{ds_uid}",
            {"id": ds_uid, "dataSetElements": [{"dataElement": {"id": de_uid}}]},
        )
    except Exception:
        pass  # not fatal for tests


async def _assign_ds_to_ou(client: DHIS2AsyncClient, ds_uid: str, ou_uid: str) -> None:
    """Best-effort association DataSet <-> OrgUnit."""
    # Preferred: POST /dataSets/{ds}/organisationUnits/{ou}
    try:
        await client.post_json(f"/api/dataSets/{ds_uid}/organisationUnits/{ou_uid}", {})
        return
    except Exception:
        pass
    # Alternate: POST /organisationUnits/{ou}/dataSets/{ds}
    try:
        await client.post_json(f"/api/organisationUnits/{ou_uid}/dataSets/{ds_uid}", {})
        return
    except Exception:
        pass
    # Fallback: PUT merge on DataSet
    try:
        await client.put_json(
            f"/api/dataSets/{ds_uid}",
            {"id": ds_uid, "organisationUnits": [{"id": ou_uid}]},
        )
    except Exception:
        pass


async def _pick_parent_ou(client: DHIS2AsyncClient) -> Optional[str]:
    """Choose a parent OU (TEST_PARENT_OU if provided, otherwise the first OU)."""
    parent = os.getenv("TEST_PARENT_OU")
    if parent:
        return parent
    ous = await client.get("/api/organisationUnits", params={"fields": "id,name", "pageSize": 1})
    arr = ous.get("organisationUnits", [])
    return arr[0]["id"] if arr else None


async def _create_org_unit(client: DHIS2AsyncClient, parent_ou: Optional[str]) -> str:
    """Create a child Organisation Unit under the given parent (if any)."""
    from datetime import date as _date

    suffix = uuid.uuid4().hex[:6]
    payload = {
        "name": f"OU Test {suffix}",
        "shortName": f"OUT{suffix}",
        "openingDate": _date.today().isoformat(),
    }
    if parent_ou:
        payload["parent"] = {"id": parent_ou}
    return await _extract_uid_from_response_or_search(client, "organisationUnits", payload)


async def _get_default_category_combo(client: DHIS2AsyncClient) -> str:
    """Try to find the 'default' CategoryCombo UID; fall back to a common demo UID."""
    try:
        res = await client.get(
            "/api/categoryCombos",
            params={"fields": "id,name", "filter": "name:eq:default", "paging": "false"},
        )
        arr = res.get("categoryCombos") or []
        if arr:
            return arr[0]["id"]
    except Exception:
        pass
    # Fallback demo UID (may differ on your instance)
    return "bjDvmb4bfuf"


# ---- Self-contained full metadata stack fixture ------------------------------


@pytest_asyncio.fixture
async def full_metadata_stack(requires_env, requires_mutations):
    """
    Provision a minimal but complete stack required to post data:
      - DataSet (Monthly)  [reuses TEST_DATASET_UID if provided]
      - DataElement (INTEGER)
      - OrganisationUnit (child of TEST_PARENT_OU or the first OU)
      - Link DE -> DS and DS <-> OU
    Yields: dict(orgUnit, dataSet, dataElement)
    Cleans up DE + OU (and DS if created here).
    """
    # Open our own client (self-contained fixture)
    settings = Settings()
    client_cm = DHIS2AsyncClient.from_settings(settings)
    client = await client_cm.__aenter__()

    pin_ds = os.getenv("TEST_DATASET_UID")
    ds_uid: Optional[str] = None
    de_uid: Optional[str] = None
    ou_uid: Optional[str] = None

    try:
        # Reuse an existing DataSet if pinned
        if pin_ds:
            ds_uid = pin_ds
        else:
            # Create a DataSet with a complete payload
            default_cc = await _get_default_category_combo(client)
            ds_payload = {
                "name": f"DS Test {uuid.uuid4().hex[:6]}",
                "shortName": f"DS{uuid.uuid4().hex[:4]}",
                "periodType": "Monthly",
                "openFuturePeriods": 1,
                "expiryDays": 0,
                "categoryCombo": {"id": default_cc},
            }
            try:
                ds_uid = await _extract_uid_from_response_or_search(client, "dataSets", ds_payload)
            except Exception as e:
                # If the server refuses DS creation, skip this full-stack test
                if isinstance(e, Conflict):
                    pytest.skip(
                        f"Server refused DataSet creation (skipping full stack): "
                        f"{getattr(e, 'details', {}).get('message', 'conflict')}"
                    )
                raise

        # Create a DataElement
        de_uid = await _extract_uid_from_response_or_search(
            client,
            "dataElements",
            {
                "name": f"DE Test {uuid.uuid4().hex[:6]}",
                "shortName": f"DE{uuid.uuid4().hex[:4]}",
                "domainType": "AGGREGATE",
                "valueType": "INTEGER",
                "aggregationType": "SUM",
            },
        )

        # Create an Organisation Unit (child of TEST_PARENT_OU or first OU)
        parent_ou = await _pick_parent_ou(client)
        ou_uid = await _create_org_unit(client, parent_ou)

        # Link DE -> DS and DS <-> OU
        await _link_de_to_ds(client, de_uid, ds_uid)  # type: ignore[arg-type]
        await _assign_ds_to_ou(client, ds_uid, ou_uid)  # type: ignore[arg-type]

        # Hand off to the test
        yield {"orgUnit": ou_uid, "dataSet": ds_uid, "dataElement": de_uid}

    finally:
        # Teardown (best-effort). Never delete a pinned DS.
        try:
            if ou_uid:
                await client.delete(f"/api/organisationUnits/{ou_uid}")
        except Exception:
            pass
        try:
            if de_uid:
                await client.delete(f"/api/dataElements/{de_uid}")
        except Exception:
            pass
        if ds_uid and not pin_ds:
            try:
                await client.delete(f"/api/dataSets/{ds_uid}")
            except Exception:
                pass

        # Close the client we opened at the start of the fixture
        await client_cm.__aexit__(None, None, None)
