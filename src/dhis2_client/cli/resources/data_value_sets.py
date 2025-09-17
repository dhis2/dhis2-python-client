from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, TYPE_CHECKING
from urllib.parse import urlencode

import typer
from click import Choice  # <- enum-like validation

from ..common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from ..output import render_output

if TYPE_CHECKING:
    from dhis2_client import DHIS2Client, DHIS2AsyncClient

dvs_app = typer.Typer(help="Data value set import/export (JSON)")

Option = typer.Option


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
    data_set: Annotated[Optional[str], Option("--data-set", help="dataSet UID")] = None,
    period: Annotated[Optional[str], Option("--period", help="e.g. 202401 or 2024Q1")] = None,
    org_unit: Annotated[Optional[str], Option("--org-unit")] = None,
    start_date: Annotated[Optional[str], Option("--start-date")] = None,
    end_date: Annotated[Optional[str], Option("--end-date")] = None,
    children: Annotated[bool, Option("--children/--no-children")] = False,
    param: Annotated[List[str], Option("--param", help="Extra query params key=value")] = [],
    dest: Annotated[Optional[str], Option("--dest", help="Output path or '-' for stdout")] = "-",
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    engine: Annotated[
        str,
        Option("--engine", click_type=Choice(["sync", "async"], case_sensitive=False), help="Default: sync")
    ] = "sync",
    profile: Annotated[Optional[str], Option("--profile")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
):
    """Export a dataValueSet as JSON to file or stdout."""
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg: CLISettings = resolve_settings(
        base_url=base_url,
        username=username,
        password=pw,
        token=token,
        timeout=None,
        verify_ssl=None,
        log_level=None,
        engine=engine.lower(),
        output="json",
        fields=[],
        jq=None,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
    )
    settings = make_settings(cfg)

    params: Dict[str, Any] = {"format": "json"}
    if data_set:
        params["dataSet"] = data_set
    if period:
        params["period"] = period
    if org_unit:
        params["orgUnit"] = org_unit
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date
    if children:
        params["children"] = True
    params.update(_parse_params(param))

    path = "/api/dataValueSets"

    try:
        if cfg.engine == "async":
            from dhis2_client import DHIS2AsyncClient

            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.get(path, params=params)
            data = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                data = client.get(path, params=params)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    _write_json_to(data, dest)


@dvs_app.command("import")
def import_(
    source: Annotated[str, Option("--source", help="JSON text, @file.json, or '-' for stdin")],
    dry_run: Annotated[bool, Option("--dry-run/--commit")] = False,
    param: Annotated[
        List[str],
        Option("--param", help="Extra query params key=value (e.g., importStrategy=CREATE_AND_UPDATE)")
    ] = [],
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    engine: Annotated[
        str,
        Option("--engine", click_type=Choice(["sync", "async"], case_sensitive=False), help="Default: sync")
    ] = "sync",
    profile: Annotated[Optional[str], Option("--profile")] = None,
    output: Annotated[
        str,
        Option("--output", "-o", click_type=Choice(["table", "json", "yaml"], case_sensitive=False))
    ] = "json",
    jq: Annotated[Optional[str], Option("--jq")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
):
    """Import a dataValueSet from JSON (stdin or file)."""
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    payload = _read_json_from(source)

    cfg: CLISettings = resolve_settings(
        base_url=base_url,
        username=username,
        password=pw,
        token=token,
        timeout=None,
        verify_ssl=None,
        log_level=None,
        engine=engine.lower(),
        output=output.lower(),
        fields=[],
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
    )
    settings = make_settings(cfg)

    params: Dict[str, Any] = {}
    if dry_run:
        params["dryRun"] = True
    params.update(_parse_params(param))

    path = "/api/dataValueSets"
    # Note: keeping query in URL to avoid assuming client.post_json supports params=.
    path_q = f"{path}?{urlencode(params, doseq=True)}" if params else path

    try:
        if cfg.engine == "async":
            from dhis2_client import DHIS2AsyncClient

            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.post_json(path_q, payload=payload)
            res = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                res = client.post_json(path_q, payload=payload)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)
