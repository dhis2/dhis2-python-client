import os

import pytest

from dhis2_client import DHIS2Client

BASE_URL = os.environ.get("DHIS2_BASE_URL")
USERNAME = os.environ.get("DHIS2_USERNAME")
PASSWORD = os.environ.get("DHIS2_PASSWORD")
TOKEN = os.environ.get("DHIS2_TOKEN")

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    if not BASE_URL or not (TOKEN or (USERNAME and PASSWORD)):
        pytest.skip(
            "Set DHIS2_BASE_URL and either TOKEN or USERNAME/PASSWORD for integration tests."
        )
    return DHIS2Client(base_url=BASE_URL, username=USERNAME, password=PASSWORD, token=TOKEN)


def test_system_info(client):
    info = client.get("/api/system/info")
    assert isinstance(info, dict)
    # Loose shape checks
    assert "version" in info and "systemName" in info


def test_list_users_readonly(client):
    # May be empty on some servers; ensure iteration doesn't break
    it = client.get_users(fields="id,username", pageSize=5)
    pulled = 0
    for _ in it:
        pulled += 1
        if pulled >= 5:
            break
    assert pulled >= 0


def test_list_org_units(client):
    it = client.get_organisation_units(level=1, fields="id,displayName", pageSize=5)
    pulled = 0
    for _ in it:
        pulled += 1
        if pulled >= 5:
            break
    assert pulled >= 0
