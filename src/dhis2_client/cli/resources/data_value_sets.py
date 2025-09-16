from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import typer
from dhis2_client import DHIS2AsyncClient, DHIS2Client

from ..common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from ..output import render_output  # <-- added

dvs_app = typer.Typer(help="Data value set import/export (JSON)")

def _parse_params(items: List[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for p in items:
        if "=" not in p:
            raise typer.BadParameter(f"Invalid --param '{p}', expected key=value")
        k, v = p.split("=", 1)
        params[k] = v
    return params

def _read_json_from(source: str) -> Any:
    if source == "-":
        return json.loads(sys.stdin.read())
    if source.startswith("@"):
        p = Path(source[1:])
        return json.loads(p.read_text(encoding="utf-8"))
    # raw JSON
    return json.loads(source)

def _write_json_to(data: Any, dest: str | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if dest == "-" or dest is None:
        sys.stdout.write(text + "\n")
        return
    Path(dest).write_text(text, encoding="utf-8")

@dvs_app.command("export")
def export(
    data_set: Optional[str] = typer.Option(None, "--data-set", help="dataSet UID"),
    period: Optional[str] = typer.Option(None, "--period", help="e.g. 202401 or 2024Q1"),
    org_unit: Optional[str] = typer.Option(None, "--org-unit"),
    start_date: Optional[str] = typer.Option(None, "--start-date"),
    end_date: Optional[str] = typer.Option(None, "--end-date"),
    children: bool = typer.Option(False, "--children/--no-children"),
    param: list[str] = typer.Option([], "--param", help="Extra query params key=value"),
    dest: Optional[str] = typer.Option("-", "--dest", help="Output path or '-' for stdout"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    username: Optional[str] = typer.Option(None, "--username"),
    password: Optional[str] = typer.Option(None, "--password", prompt=False, hide_input=True),
    token: Optional[str] = typer.Option(None, "--token"),
    password_stdin: bool = typer.Option(False, "--password-stdin"),
    engine: Optional[str] = typer.Option(None, "--engine", help="sync|async"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    verbose: bool = typer.Option(False, "--verbose", help="Show full error details on failure."),
):
    """Export a dataValueSet as JSON to file or stdout."""
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg: CLISettings = resolve_settings(
        base_url=base_url, username=username, password=pw, token=token,
        timeout=None, verify_ssl=None, log_level=None,
        engine=engine, output="json", fields=[], jq=None, profile=profile,
        page_size=None, all_pages=False, password_stdin=password_stdin, array_key=None
    )
    settings = make_settings(cfg)

    params: Dict[str, Any] = {"format": "json"}
    if data_set: params["dataSet"] = data_set
    if period: params["period"] = period
    if org_unit: params["orgUnit"] = org_unit
    if start_date: params["startDate"] = start_date
    if end_date: params["endDate"] = end_date
    if children: params["children"] = True
    params.update(_parse_params(param))

    path = "/api/dataValueSets"

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.get(path, params=params)
            data = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                data = client.get(path, params=params)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    _write_json_to(data, dest)

@dvs_app.command("import")
def import_(
    source: str = typer.Option(..., "--source", help="JSON text, @file.json, or '-' for stdin"),
    dry_run: bool = typer.Option(False, "--dry-run/--commit"),
    param: list[str] = typer.Option([], "--param", help="Extra query params key=value (e.g., importStrategy=CREATE_AND_UPDATE)"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    username: Optional[str] = typer.Option(None, "--username"),
    password: Optional[str] = typer.Option(None, "--password", prompt=False, hide_input=True),
    token: Optional[str] = typer.Option(None, "--token"),
    password_stdin: bool = typer.Option(False, "--password-stdin"),
    engine: Optional[str] = typer.Option(None, "--engine", help="sync|async"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    output: Optional[str] = typer.Option("json", "--output"),
    jq: Optional[str] = typer.Option(None, "--jq"),
    verbose: bool = typer.Option(False, "--verbose", help="Show full error details on failure."),
):
    """Import a dataValueSet from JSON (stdin or file)."""
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    payload = _read_json_from(source)

    cfg: CLISettings = resolve_settings(
        base_url=base_url, username=username, password=pw, token=token,
        timeout=None, verify_ssl=None, log_level=None,
        engine=engine, output=output, fields=[], jq=jq, profile=profile,
        page_size=None, all_pages=False, password_stdin=password_stdin, array_key=None
    )
    settings = make_settings(cfg)

    params: Dict[str, Any] = {}
    if dry_run:
        params["dryRun"] = True
    params.update(_parse_params(param))

    path = "/api/dataValueSets"
    path_q = f"{path}?{urlencode(params, doseq=True)}" if params else path  # <-- ensure params are sent

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.post_json(path_q, payload=payload)
            res = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                res = client.post_json(path_q, payload=payload)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)
