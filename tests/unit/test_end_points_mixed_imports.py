from __future__ import annotations

from dhis2_client import DHIS2AsyncClient, DHIS2Client, Settings


def test_init_exports_sync_async():
    assert DHIS2Client and DHIS2AsyncClient and Settings
