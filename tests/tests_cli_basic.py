from __future__ import annotations

import json
from typer.testing import CliRunner

from dhis2_client.cli.app import app

runner = CliRunner()


def test_help():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "DHIS2 Web API CLI" in res.stdout


def test_system_info_smoke(monkeypatch):
    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *exc):
            return False
        async def get_system_info(self):
            return {"version": "2.41.0", "systemName": "Demo"}

    class FakeFactory:
        @staticmethod
        def from_settings(settings):
            return FakeClient()

    import dhis2_client.cli.app as appmod

    monkeypatch.setattr(appmod, "DHIS2AsyncClient", FakeFactory)

    res = runner.invoke(app, ["system-info", "--output", "json"])
    assert res.exit_code == 0
    assert "Demo" in res.stdout


def test_get_basic(monkeypatch):
    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *exc):
            return False
        async def get(self, path, params=None):
            assert path.startswith("/api/") or path.startswith("api/")
            return {"pager": {"page": 1, "pageSize": 1, "total": 1}, "dataElements": [{"id": "A", "name": "Alpha"}]}

    class FakeFactory:
        @staticmethod
        def from_settings(settings):
            return FakeClient()

    import dhis2_client.cli.app as appmod

    monkeypatch.setattr(appmod, "DHIS2AsyncClient", FakeFactory)

    res = runner.invoke(app, ["get", "/api/dataElements", "--all", "--output", "ndjson"])
    assert res.exit_code == 0
    lines = [ln for ln in res.stdout.splitlines() if ln.strip()]
    assert any(json.loads(ln).get("id") == "A" for ln in lines)