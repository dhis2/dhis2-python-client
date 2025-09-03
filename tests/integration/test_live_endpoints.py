import os

import pytest
from dhis2_client import DHIS2AsyncClient, Settings

requires_env = pytest.mark.skipif(
    not os.path.exists(".env") and not os.getenv("DHIS2_BASE_URL"),
    reason="Integration tests require a .env or env vars",
)


@pytest.mark.integration
@requires_env
@pytest.mark.asyncio
async def test_live_system_info():
    settings = Settings()
    async with DHIS2AsyncClient.from_settings(settings) as client:
        info = await client.get_system_info()
        assert info.version


@pytest.mark.integration
@requires_env
@pytest.mark.asyncio
async def test_live_list_organisation_units():
    settings = Settings()
    async with DHIS2AsyncClient.from_settings(settings) as client:
        ous = await client.get_organisation_units(fields=["id", "name"], page_size=1)
        assert isinstance(ous, list)
