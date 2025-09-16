from __future__ import annotations

import httpx
import respx
from dhis2_client import DHIS2Client, Settings


def test_get_system_info_sync():
    settings = Settings(base_url="http://test")
    with DHIS2Client.from_settings(settings) as client:
        with respx.mock(base_url="http://test") as router:
            router.get("/api/system/info").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "version": "2.40.0",
                        "contextPath": "http://test",
                        "serverDate": "2025-01-01T00:00:00.000Z",
                    },
                )
            )
            info = client.get_system_info()
            assert info.version == "2.40.0"


def test_paging_data_elements_two_pages_sync():
    settings = Settings(base_url="http://test")
    with DHIS2Client.from_settings(settings) as client:
        with respx.mock(base_url="http://test") as router:
            route = router.get("/api/dataElements")
            route.mock(
                side_effect=[
                    # First call -> get_data_elements(paging=True)
                    httpx.Response(
                        200,
                        json={
                            "dataElements": [{"id": "de1", "name": "One"}],
                            "pager": {"page": 1, "pageCount": 2},
                        },
                    ),
                    # Second call -> list_all first page
                    httpx.Response(
                        200,
                        json={
                            "dataElements": [{"id": "de1", "name": "One"}],
                            "pager": {"page": 1, "pageCount": 2},
                        },
                    ),
                    # Third call -> list_all second page
                    httpx.Response(
                        200,
                        json={
                            "dataElements": [{"id": "de2", "name": "Two"}],
                            "pager": {"page": 2, "pageCount": 2},
                        },
                    ),
                ]
            )
            # first-page call
            items = client.get_data_elements(fields=["id", "name"], page_size=1, paging=True)
            assert len(items) == 1 and items[0].id == "de1"

            # all pages
            all_items = client.list_all_data_elements(fields=["id", "name"], page_size=1)
            assert [i.id for i in all_items] == ["de1", "de2"]
