from __future__ import annotations
import sys
from typing import Optional, Dict, Any
import typer

from ..common import resolve_settings, make_settings, run_async, CLISettings, print_http_error
from ..output import render_output
from dhis2_client import DHIS2AsyncClient, DHIS2Client

data_values_app = typer.Typer(help="Single data value helpers")

# NOTE: For read/delete we use /api/dataValues; for upsert we use /api/dataValueSets with a single item.


@data_values_app.command("get")
def get_value(
    de: str = typer.Option(..., "--de", help="Data Element ID"),
    pe: str = typer.Option(..., "--pe", help="Period, e.g. 202401"),
    ou: str = typer.Option(..., "--ou", help="Org Unit ID"),
    co: Optional[str] = typer.Option(None, "--co", help="CategoryOptionCombo (C.O.C)"),
    aoc: Optional[str] = typer.Option(None, "--aoc", help="AttributeOptionCombo (A.O.C)"),
    cc: Optional[str] = typer.Option(None, "--cc", help="Category combo ID (for classic form)"),
    cp: Optional[str] = typer.Option(None, "--cp", help="Category options pipe list (for classic form)"),
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
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg: CLISettings = resolve_settings(
        base_url=base_url, username=username, password=pw, token=token,
        timeout=None, verify_ssl=None, log_level=None,
        engine=engine, output=output, fields=[], jq=jq, profile=profile,
        page_size=None, all_pages=False, password_stdin=password_stdin, array_key=None
    )
    settings = make_settings(cfg)

    params: Dict[str, Any] = {"de": de, "pe": pe, "ou": ou}
    if co: params["co"] = co
    if aoc: params["cc"] = "null"; params["cp"] = "null"; params["aoc"] = aoc  # DHIS2 interprets aoc when provided
    if cc: params["cc"] = cc
    if cp: params["cp"] = cp

    path = "/api/dataValues"

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

    render_output(data, output=cfg.output, fields=[], jq=cfg.jq)


@data_values_app.command("delete")
def delete_value(
    de: str = typer.Option(..., "--de"),
    pe: str = typer.Option(..., "--pe"),
    ou: str = typer.Option(..., "--ou"),
    co: Optional[str] = typer.Option(None, "--co"),
    aoc: Optional[str] = typer.Option(None, "--aoc"),
    cc: Optional[str] = typer.Option(None, "--cc"),
    cp: Optional[str] = typer.Option(None, "--cp"),
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
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg: CLISettings = resolve_settings(
        base_url=base_url, username=username, password=pw, token=token,
        timeout=None, verify_ssl=None, log_level=None,
        engine=engine, output=output, fields=[], jq=jq, profile=profile,
        page_size=None, all_pages=False, password_stdin=password_stdin, array_key=None
    )
    settings = make_settings(cfg)

    params: Dict[str, Any] = {"de": de, "pe": pe, "ou": ou}
    if co: params["co"] = co
    if aoc: params["aoc"] = aoc
    if cc: params["cc"] = cc
    if cp: params["cp"] = cp

    path = "/api/dataValues"

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.delete(path + "?" + "&".join(f"{k}={v}" for k,v in params.items()))
            res = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                # some servers require querystring on DELETE
                res = client.delete(path + "?" + "&".join(f"{k}={v}" for k,v in params.items()))
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)


@data_values_app.command("upsert")
def upsert_value(
    de: str = typer.Option(..., "--de"),
    pe: str = typer.Option(..., "--pe"),
    ou: str = typer.Option(..., "--ou"),
    value: str = typer.Option(..., "--value"),
    co: Optional[str] = typer.Option(None, "--co"),
    aoc: Optional[str] = typer.Option(None, "--aoc"),
    comment: Optional[str] = typer.Option(None, "--comment"),
    follow_up: bool = typer.Option(False, "--follow-up/--no-follow-up"),
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
    """
    Implements upsert via POST /api/dataValueSets with a single dataValues item.
    Safer and simpler than the form-encoded /api/dataValues endpoint.
    """
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg: CLISettings = resolve_settings(
        base_url=base_url, username=username, password=pw, token=token,
        timeout=None, verify_ssl=None, log_level=None,
        engine=engine, output=output, fields=[], jq=jq, profile=profile,
        page_size=None, all_pages=False, password_stdin=password_stdin, array_key=None
    )
    settings = make_settings(cfg)

    dv: Dict[str, Any] = {"dataElement": de, "period": pe, "orgUnit": ou, "value": value}
    if co: dv["categoryOptionCombo"] = co
    if aoc: dv["attributeOptionCombo"] = aoc
    if comment: dv["comment"] = comment
    if follow_up: dv["followUp"] = True

    payload = {"dataValues": [dv]}

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.post_json("/api/dataValueSets", payload=payload)
            res = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                res = client.post_json("/api/dataValueSets", payload=payload)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)
