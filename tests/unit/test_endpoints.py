import httpx
import pytest
import respx
from dhis2_client import DHIS2AsyncClient, Settings


@pytest.mark.asyncio
async def test_get_organisation_units_endpoint_and_parsing():
    settings = Settings(base_url="http://test", token="secret")
    async with DHIS2AsyncClient.from_settings(settings) as client:
        with respx.mock(base_url="http://test") as router:
            route = router.get("/api/organisationUnits").mock(
                return_value=httpx.Response(200, json={"organisationUnits": [{"id": "A", "name": "HQ"}]})
            )
            ous = await client.get_organisation_units(fields=["id", "name"], page_size=2, paging=False, as_dict=False)
            assert route.called and len(ous) == 1 and ous[0].id == "A"
