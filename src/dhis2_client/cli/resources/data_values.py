from __future__ import annotations

import sys
from typing import Annotated, Any, Dict, Optional, TYPE_CHECKING, List

import typer
from click import Choice  # validate enum-like options

from ..common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from ..output import render_output

if TYPE_CHECKING:
    from dhis2_client import DHIS2Client, DHIS2AsyncClient

data_values_app = typer.Typer(help="Single data value helpers")

Option = typer.Option


# NOTE: For read/delete we use /api/dataValues; for upsert we use /api/dataValueSets with a single item.

@data_values_app.command("get")
def get_value(
    de: Annotated[str, Option("--de", help="Data Element ID")],
    pe: Annotated[str, Option("--pe", help="Period, e.g. 202401")],
    ou: Annotated[str, Option("--ou", help="Org Unit ID")],
    co: Annotated[Optional[str], Option("--co", help="CategoryOptionCombo (C.O.C)")] = None,
    aoc: Annotated[Optional[str], Option("--aoc", help="AttributeOptionCombo (A.O.C)")] = None,
    cc: Annotated[Optional[str], Option("--cc", help="Category combo ID (classic form)")] = None,
    cp: Annotated[Optional[str], Option("--cp", help="Category options pipe list (classic form)")] = None,
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    engine: Annotated[
        str,
        Option("--engine", click_type=Choice(["sync", "async"], case_sensitive=False), help="sync|async (default: sync)")
    ] = "sync",
    profile: Annotated[Optional[str], Option("--profile")] = None,
    output: Annotated[
        str,
        Option("--output", "-o", click_type=Choice(["table", "json", "yaml"], case_sensitive=False))
    ] = "json",
    jq: Annotated[Optional[str], Option("--jq")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
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

    params: Dict[str, Any] = {"de": de, "pe": pe, "ou": ou}
    if co:
        params["co"] = co
    if aoc:
        params["aoc"] = aoc  # when aoc is provided, omit cc/cp entirely
    else:
        if cc:
            params["cc"] = cc
        if cp:
            params["cp"] = cp

    path = "/api/dataValues"

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

    render_output(data, output=cfg.output, fields=[], jq=cfg.jq)


@data_values_app.command("delete")
def delete_value(
    de: Annotated[str, Option("--de")],
    pe: Annotated[str, Option("--pe")],
    ou: Annotated[str, Option("--ou")],
    co: Annotated[Optional[str], Option("--co")] = None,
    aoc: Annotated[Optional[str], Option("--aoc")] = None,
    cc: Annotated[Optional[str], Option("--cc")] = None,
    cp: Annotated[Optional[str], Option("--cp")] = None,
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    engine: Annotated[
        str,
        Option("--engine", click_type=Choice(["sync", "async"], case_sensitive=False), help="sync|async (default: sync)")
    ] = "sync",
    profile: Annotated[Optional[str], Option("--profile")] = None,
    output: Annotated[
        str,
        Option("--output", "-o", click_type=Choice(["table", "json", "yaml"], case_sensitive=False))
    ] = "json",
    jq: Annotated[Optional[str], Option("--jq")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
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

    params: Dict[str, Any] = {"de": de, "pe": pe, "ou": ou}
    if co:
        params["co"] = co
    if aoc:
        params["aoc"] = aoc
    else:
        if cc:
            params["cc"] = cc
        if cp:
            params["cp"] = cp

    path = "/api/dataValues"

    try:
        if cfg.engine == "async":
            from dhis2_client import DHIS2AsyncClient

            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    # use params= for safe URL encoding
                    return await client.delete(path, params=params)
            res = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                res = client.delete(path, params=params)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)


@data_values_app.command("upsert")
def upsert_value(
    de: Annotated[str, Option("--de")],
    pe: Annotated[str, Option("--pe")],
    ou: Annotated[str, Option("--ou")],
    value: Annotated[str, Option("--value")],
    co: Annotated[Optional[str], Option("--co")] = None,
    aoc: Annotated[Optional[str], Option("--aoc")] = None,
    comment: Annotated[Optional[str], Option("--comment")] = None,
    follow_up: Annotated[bool, Option("--follow-up/--no-follow-up")] = False,
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    engine: Annotated[
        str,
        Option("--engine", click_type=Choice(["sync", "async"], case_sensitive=False), help="sync|async (default: sync)")
    ] = "sync",
    profile: Annotated[Optional[str], Option("--profile")] = None,
    output: Annotated[
        str,
        Option("--output", "-o", click_type=Choice(["table", "json", "yaml"], case_sensitive=False))
    ] = "json",
    jq: Annotated[Optional[str], Option("--jq")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
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

    dv: Dict[str, Any] = {"dataElement": de, "period": pe, "orgUnit": ou, "value": value}
    if co:
        dv["categoryOptionCombo"] = co
    if aoc:
        dv["attributeOptionCombo"] = aoc
    if comment:
        dv["comment"] = comment
    if follow_up:
        dv["followUp"] = True

    payload = {"dataValues": [dv]}

    try:
        if cfg.engine == "async":
            from dhis2_client import DHIS2AsyncClient

            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.post_json("/api/dataValueSets", payload=payload)
            res = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                res = client.post_json("/api/dataValueSets", payload=payload)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)
