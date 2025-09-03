import os
import uuid

import pytest
from dhis2_client import DHIS2AsyncClient, Settings
from dhis2_client.exceptions import NotFound

MUTATIONS_ENABLED = os.getenv("ALLOW_DHIS2_MUTATIONS", "").lower() in {"1", "true", "yes"}

requires_env = pytest.mark.skipif(
    not os.path.exists(".env") and not os.getenv("DHIS2_BASE_URL"),
    reason="Integration tests require a .env or env vars",
)
requires_mutation = pytest.mark.skipif(
    not MUTATIONS_ENABLED, reason="Set ALLOW_DHIS2_MUTATIONS=true to run mutation tests"
)


@pytest.mark.integration
@requires_env
@requires_mutation
@pytest.mark.asyncio
async def test_metadata_data_element_lifecycle():
    settings = Settings()
    async with DHIS2AsyncClient.from_settings(settings) as client:
        name = f"DE Test {uuid.uuid4().hex[:6]}"
        create_resp = await client.post_json(
            "/api/dataElements",
            {
                "name": name,
                "shortName": f"DE{uuid.uuid4().hex[:4]}",
                "domainType": "AGGREGATE",
                "valueType": "INTEGER",
                "aggregationType": "SUM",
            },
        )
        uid = (create_resp.get("response", {}) or {}).get("uid") or create_resp.get("id") or create_resp.get("uid")
        if not uid:
            search = await client.get(
                "/api/dataElements", params={"fields": "id,name", "paging": "false", "filter": f"name:eq:{name}"}
            )
            uid = search.get("dataElements", [{}])[0]["id"]
        got = await client.get(f"/api/dataElements/{uid}")
        assert got.get("id") == uid
        await client.delete(f"/api/dataElements/{uid}")
        with pytest.raises(NotFound):
            await client.get(f"/api/dataElements/{uid}")
