import json

import httpx
import pytest

from dhis2_client import DHIS2Client

BASE = "http://test"


@pytest.mark.unit
def test_log_level_config_applies(respx_mock, capsys):
    # Mock a simple GET
    respx_mock.get(f"{BASE}/api/system/info").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    # INFO level + text format to stdout
    c = DHIS2Client(BASE, log_level="INFO", log_format="text", log_destination="stdout")
    c.get("/api/system/info")

    out = capsys.readouterr().out  # captured stdout
    assert "Request GET /api/system/info" in out  # message from client logger


@pytest.mark.unit
def test_log_json_format(respx_mock, capsys):
    respx_mock.get(f"{BASE}/api/system/info").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    c = DHIS2Client(BASE, log_level="INFO", log_format="json", log_destination="stdout")
    c.get("/api/system/info")

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)  # should be valid JSON
    assert payload["level"] == "INFO"
    assert payload["message"].startswith("Request GET /api/system/info")
