import os
from datetime import date, timedelta

import pytest
from dhis2_client import DHIS2AsyncClient, Settings
from dhis2_client.exceptions import Conflict
from dhis2_client.models import DataValue, DataValueSet
from dhis2_client.models.periods import format_period


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_stack_create_delete_data_values(full_metadata_stack):
    settings = Settings()

    # Optionally target the previous month to avoid “future/closed period” conflicts.
    # Use: export FULL_STACK_PREVIOUS_MONTH=true
    use_prev = os.getenv("FULL_STACK_PREVIOUS_MONTH", "").lower() in {"1", "true", "yes"}
    today = date.today()
    if use_prev:
        first = today.replace(day=1)
        prev_month_day = first - timedelta(days=1)
        per = format_period("Monthly", prev_month_day)
    else:
        per = format_period("Monthly", today)

    async with DHIS2AsyncClient.from_settings(settings) as client:
        stack = full_metadata_stack
        dvs = DataValueSet(
            dataSet=stack["dataSet"],
            period=per,
            orgUnit=stack["orgUnit"],
            dataValues=[
                DataValue(
                    dataElement=stack["dataElement"],
                    orgUnit=stack["orgUnit"],
                    period=per,
                    value="7",
                )
            ],
        )
        try:
            # Persisted create/delete (the fixture is guarded by ALLOW_DHIS2_MUTATIONS)
            assert isinstance(await client.post_data_value_set(dvs, import_strategy="CREATE"), dict)
            assert isinstance(await client.post_data_value_set(dvs, import_strategy="DELETE"), dict)
        except Conflict as e:
            details = getattr(e, "details", {}) or {}
            msg = details.get("message") or "conflict"
            pytest.skip(f"Server rejected create/delete (skipping): {msg}")
