from __future__ import annotations

import sys
from typing import Annotated, Any, Dict, Optional
from urllib.parse import urlencode

import typer
from dhis2_client import DHIS2AsyncClient, DHIS2Client

from ..common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from ..output import render_output

data_values_app = typer.Typer(help="Single data value helpers")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_params(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove keys with None / "" / "null" / "none" (case-insensitive).
    Convert booleans to the DHIS2-typical "true"/"false" strings if needed.
    """
    cleaned: Dict[str, Any] = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, str) and v.strip().lower() in {"", "null", "none"}:
            continue
        if isinstance(v, bool):
            cleaned[k] = "true" if v else "false"
        else:
            cleaned[k] = v
    return cleaned


def _build_query_params(
    *,
    de: str,
    pe: str,
    ou: str,
    co: Optional[str] = None,
    aoc: Optional[str] = None,
    cc: Optional[str] = None,
    cp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    DHIS2 rules:
    - If AOC is provided, don't send CC/CP at all.
    - If AOC is not provided, CC/CP (classic form) may be used.
    """
    params: Dict[str, Any] = {"de": de, "pe": pe, "ou": ou}
    if aoc:
        params["aoc"] = aoc
        # DO NOT send cc/cp when aoc is present
    else:
        if co:
            params["co"] = co
        if cc:
            params["cc"] = cc
        if cp:
            params["cp"] = cp
    return _clean_params(params)


# NOTE: For read/delete we use /api/dataValues; for upsert we use /api/dataValueSets with a single item.

@data_values_app.command("get")
def get_value(
    de: Annotated[str, typer.Option(..., "--de", help="Data Element ID")],
    pe: Annotated[str, typer.Option(..., "--pe", help="Period, e.g. 202401")],
    ou: Annotated[str, typer.Option(..., "--ou", help="Org Unit ID")],
    co: Annotated[Optional[str], typer.Option(None, "--co", help="CategoryOptionCombo (C.O.C)")],
    aoc: Annotated[Optional[str], typer.Option(None, "--aoc", help="AttributeOptionCombo (A.O.C)")],
    cc: Annotated[Optional[str], typer.Option(None, "--cc", help="Category combo ID (for classic form)")],
    cp: Annotated[Optional[str], typer.Option(None, "--cp", help="Category options pipe list (for classic form)")],
    base_url: Annotated[Optional[str], typer.Option(None, "--base-url")],
    username: Annotated[Optional[str], typer.Option(None, "--username")],
    password: Annotated[Optional[str], typer.Option(None, "--password", prompt=False, hide_input=True)],
    token: Annotated[Optional[str], typer.Option(None, "--token")],
    password_stdin: Annotated[bool, typer.Option(False, "--password-stdin")],
    engine: Annotated[Optional[str], typer.Option(None, "--engine", help="sync|async")],
    profile: Annotated[Optional[str], typer.Option(None, "--profile")],
    output: Annotated[Optional[str], typer.Option("json", "--output")],
    jq: Annotated[Optional[str], typer.Option(None, "--jq")],
    verbose: Annotated[bool, typer.Option(False, "--verbose", help="Show full error details on failure.")],
):
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
        engine=engine,
        output=output,
        fields=[],
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
    )
    settings = make_settings(cfg)

    params = _build_query_params(de=de, pe=pe, ou=ou, co=co, aoc=aoc, cc=cc, cp=cp)
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
        raise typer.Exit(code=4) from e

    render_output(data, output=cfg.output, fields=[], jq=cfg.jq)


@data_values_app.command("delete")
def delete_value(
    de: Annotated[str, typer.Option(..., "--de")],
    pe: Annotated[str, typer.Option(..., "--pe")],
    ou: Annotated[str, typer.Option(..., "--ou")],
    co: Annotated[Optional[str], typer.Option(None, "--co")],
    aoc: Annotated[Optional[str], typer.Option(None, "--aoc")],
    cc: Annotated[Optional[str], typer.Option(None, "--cc")],
    cp: Annotated[Optional[str], typer.Option(None, "--cp")],
    base_url: Annotated[Optional[str], typer.Option(None, "--base-url")],
    username: Annotated[Optional[str], typer.Option(None, "--username")],
    password: Annotated[Optional[str], typer.Option(None, "--password", prompt=False, hide_input=True)],
    token: Annotated[Optional[str], typer.Option(None, "--token")],
    password_stdin: Annotated[bool, typer.Option(False, "--password-stdin")],
    engine: Annotated[Optional[str], typer.Option(None, "--engine", help="sync|async")],
    profile: Annotated[Optional[str], typer.Option(None, "--profile")],
    output: Annotated[Optional[str], typer.Option("json", "--output")],
    jq: Annotated[Optional[str], typer.Option(None, "--jq")],
    verbose: Annotated[bool, typer.Option(False, "--verbose", help="Show full error details on failure.")],
):
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
        engine=engine,
        output=output,
        fields=[],
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
    )
    settings = make_settings(cfg)

    params = _build_query_params(de=de, pe=pe, ou=ou, co=co, aoc=aoc, cc=cc, cp=cp)
    path = "/api/dataValues"

    try:
        if cfg.engine == "async":

            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.delete(path + "?" + urlencode(params))

            res = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                res = client.delete(path + "?" + urlencode(params))
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)


@data_values_app.command("upsert")
def upsert_value(
    de: Annotated[str, typer.Option(..., "--de")],
    pe: Annotated[str, typer.Option(..., "--pe")],
    ou: Annotated[str, typer.Option(..., "--ou")],
    value: Annotated[str, typer.Option(..., "--value")],
    co: Annotated[Optional[str], typer.Option(None, "--co")],
    aoc: Annotated[Optional[str], typer.Option(None, "--aoc")],
    comment: Annotated[Optional[str], typer.Option(None, "--comment")],
    follow_up: Annotated[bool, typer.Option(False, "--follow-up/--no-follow-up")],
    base_url: Annotated[Optional[str], typer.Option(None, "--base-url")],
    username: Annotated[Optional[str], typer.Option(None, "--username")],
    password: Annotated[Optional[str], typer.Option(None, "--password", prompt=False, hide_input=True)],
    token: Annotated[Optional[str], typer.Option(None, "--token")],
    password_stdin: Annotated[bool, typer.Option(False, "--password-stdin")],
    engine: Annotated[Optional[str], typer.Option(None, "--engine", help="sync|async")],
    profile: Annotated[Optional[str], typer.Option(None, "--profile")],
    output: Annotated[Optional[str], typer.Option("json", "--output")],
    jq: Annotated[Optional[str], typer.Option(None, "--jq")],
    verbose: Annotated[bool, typer.Option(False, "--verbose", help="Show full error details on failure.")],
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
        base_url=base_url,
        username=username,
        password=pw,
        token=token,
        timeout=None,
        verify_ssl=None,
        log_level=None,
        engine=engine,
        output=output,
        fields=[],
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
    )
    settings = make_settings(cfg)

    dv: Dict[str, Any] = {"dataElement": de, "period": pe, "orgUnit": ou, "value": value}
    # AOC and classic form are mutually exclusive
    if aoc:
        dv["attributeOptionCombo"] = aoc
    else:
        if co:
            dv["categoryOptionCombo"] = co
    if comment and comment.strip():
        dv["comment"] = comment
    if follow_up:
        dv["followUp"] = True

    dv = _clean_params(dv)  # ensure no null/empty values
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
        raise typer.Exit(code=4) from e

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)
