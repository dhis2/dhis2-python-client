import httpx

from dhis2_client import DHIS2Client
from dhis2_client.settings import ClientSettings


def test_default_timeouts():
    c = DHIS2Client("http://test")
    assert isinstance(c._client, httpx.Client)
    timeout = c._client.timeout

    assert timeout.connect == 60.0
    assert timeout.read == 30.0
    assert timeout.write == 30.0
    assert timeout.pool == 30.0


def test_custom_connect_timeout_kwarg():
    c = DHIS2Client("http://test", timeout=20.0, connect_timeout=75.0)
    timeout = c._client.timeout

    assert timeout.connect == 75.0
    assert timeout.read == 20.0
    assert timeout.write == 20.0
    assert timeout.pool == 20.0


def test_connect_timeout_from_settings():
    settings = ClientSettings(base_url="http://test", timeout=25.0, connect_timeout=90.0)
    c = DHIS2Client(settings=settings)
    timeout = c._client.timeout

    assert timeout.connect == 90.0
    assert timeout.read == 25.0
    assert timeout.write == 25.0
    assert timeout.pool == 25.0
