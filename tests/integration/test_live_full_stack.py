from datetime import date

import pytest
from dhis2_client import DHIS2AsyncClient, Settings
from dhis2_client.models import DataValue, DataValueSet, format_period


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_stack_create_delete_data_values(full_metadata_stack):
    # Create our own client instance to avoid relying on dhis2_client fixture
    settings = Settings()
    async with DHIS2AsyncClient.from_settings(settings) as client:
        stack = full_metadata_stack
        period = format_period("Monthly", date.today())
        dvs = DataValueSet(
            dataSet=stack["dataSet"],
            period=period,
            orgUnit=stack["orgUnit"],
            dataValues=[
                DataValue(
                    dataElement=stack["dataElement"],
                    orgUnit=stack["orgUnit"],
                    period=period,
                    value="7",
                )
            ],
        )
        # Persisted create/delete (the fixture is guarded by ALLOW_DHIS2_MUTATIONS)
        assert isinstance(await client.post_data_value_set(dvs, import_strategy="CREATE"), dict)
        assert isinstance(await client.post_data_value_set(dvs, import_strategy="DELETE"), dict)
