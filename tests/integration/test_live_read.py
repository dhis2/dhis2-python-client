import os

import pytest

from dhis2_client import DHIS2Client
from dhis2_client.settings import ClientSettings

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("DHIS2_BASE_URL")
USERNAME = os.environ.get("DHIS2_USERNAME")
PASSWORD = os.environ.get("DHIS2_PASSWORD")
TOKEN = os.environ.get("DHIS2_TOKEN")

OU_CHILD = os.environ.get("TEST_OU_CHILD", "OuChild0001")
DS_ID = os.environ.get("TEST_DS_ID", "DsMonth0001")


@pytest.mark.skipif(not BASE_URL, reason="DHIS2_BASE_URL not set")
def test_system_info_and_reads():
    cfg = ClientSettings(
        base_url=BASE_URL,
        username=USERNAME if not TOKEN else None,
        password=PASSWORD if not TOKEN else None,
        token=TOKEN,
        log_level="INFO",
        log_destination="stdout",
    )
    c = DHIS2Client(settings=cfg)

    info = c.get_system_info()
    assert "version" in info

    # Read a few users (may be empty)
    _ = list(c.get_users(fields="id,username", pageSize=3))

    # Read back org unit (if seeded)
    ou = c.get_org_unit(OU_CHILD, fields="id,displayName")
    assert ou.get("id") == OU_CHILD or ou.get("id") is None

    # Read dataset (if seeded)
    ds = c.get_data_set(DS_ID, fields="id,displayName,periodType")
    assert ds.get("periodType") in (None, "Monthly")
