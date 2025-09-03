import httpx
import pytest
import respx
from dhis2_client import DHIS2AsyncClient, Settings


@pytest.mark.asyncio
async def test_paging_data_elements_two_pages():
    settings = Settings(base_url="http://test", token="secret")
    async with DHIS2AsyncClient.from_settings(settings) as client:
        with respx.mock(base_url="http://test") as router:
            router.get("/api/dataElements").mock(
                side_effect=[
                    httpx.Response(
                        200, json={"dataElements": [{"id": "de1", "name": "One"}], "pager": {"page": 1, "pageCount": 2}}
                    ),
                    httpx.Response(
                        200, json={"dataElements": [{"id": "de2", "name": "Two"}], "pager": {"page": 2, "pageCount": 2}}
                    ),
                ]
            )
            items = await client.list_all_data_elements(fields=["id", "name"], page_size=1)
            assert [de.id for de in items] == ["de1", "de2"]
