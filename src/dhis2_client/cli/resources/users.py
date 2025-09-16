from __future__ import annotations

import sys
from typing import Annotated, Any, Dict, Optional

import typer
from dhis2_client import DHIS2AsyncClient, DHIS2Client

from ..common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from ..output import render_output
from ..utils import parse_bool_opt, to_plain_json  # ← use your helpers

users_app = typer.Typer(help="Users")

API_PATH = "/api/users"
ARRAY_KEY = "users"
DEFAULT_FIELDS = ["id", "username", "displayName", "email"]


def _normalize(res: Dict[str, Any]) -> list[dict]:
    return res.get(ARRAY_KEY, []) if isinstance(res, dict) else []


@users_app.command("list")
def list_users(
    base_url: Annotated[Optional[str], typer.Option(None, "--base-url")],
    username: Annotated[Optional[str], typer.Option(None, "--username")],
    password: Annotated[Optional[str], typer.Option(None, "--password", prompt=False, hide_input=True)],
    token: Annotated[Optional[str], typer.Option(None, "--token")],
    password_stdin: Annotated[bool, typer.Option(False, "--password-stdin")],
    engine: Annotated[Optional[str], typer.Option(None, "--engine", help="sync|async")],
    profile: Annotated[Optional[str], typer.Option(None, "--profile")],
    page_size: Annotated[Optional[int], typer.Option(None, "--page-size")],
    all_pages: Annotated[bool, typer.Option(False, "--all", help="Fetch all pages")],
    fields: Annotated[list[str], typer.Option(DEFAULT_FIELDS, "--fields")],
    output: Annotated[Optional[str], typer.Option("table", "--output")],
    jq: Annotated[Optional[str], typer.Option(None, "--jq")],
    verbose: Annotated[bool, typer.Option(False, "--verbose", help="Show full error details on failure.")],
    as_dict: Annotated[
        Optional[str],
        typer.Option(None, "--as-dict", metavar="BOOL", help="true/false. Omit to use Settings.return_models default."),
    ] = None,
) -> None:
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
        fields=fields,
        jq=jq,
        profile=profile,
        page_size=page_size,
        all_pages=all_pages,
        password_stdin=password_stdin,
        array_key=ARRAY_KEY,
        as_dict=parse_bool_opt(as_dict),  # ← threaded for consistency/global default
    )
    settings = make_settings(cfg)
    query_fields = ",".join(fields) if fields else ",".join(DEFAULT_FIELDS)

    try:
        if cfg.engine == "async":

            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    if cfg.all_pages:
                        items: list[dict] = []
                        first = await client.get(
                            API_PATH,
                            params={"paging": True, "pageSize": cfg.page_size, "page": 1, "fields": query_fields},
                        )
                        pager = int(first.get("pager", {}).get("pageCount", 1)) if isinstance(first, dict) else 1
                        items.extend(_normalize(first))
                        for p in range(2, pager + 1):
                            res = await client.get(
                                API_PATH,
                                params={"paging": True, "pageSize": cfg.page_size, "page": p, "fields": query_fields},
                            )
                            # avoid key error if response is not dict
                            items.extend(_normalize(res))
                        return items
                    res = await client.get(
                        API_PATH, params={"paging": True, "pageSize": cfg.page_size, "page": 1, "fields": query_fields}
                    )
                    return _normalize(res)

            data = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                if cfg.all_pages:
                    items: list[dict] = []
                    first = client.get(
                        API_PATH, params={"paging": True, "pageSize": cfg.page_size, "page": 1, "fields": query_fields}
                    )
                    pager = int(first.get("pager", {}).get("pageCount", 1)) if isinstance(first, dict) else 1
                    items.extend(_normalize(first))
                    for p in range(2, pager + 1):
                        res = client.get(
                            API_PATH,
                            params={"paging": True, "pageSize": cfg.page_size, "page": p, "fields": query_fields},
                        )
                        items.extend(_normalize(res))
                    data = items
                else:
                    res = client.get(
                        API_PATH, params={"paging": True, "pageSize": cfg.page_size, "page": 1, "fields": query_fields}
                    )
                    data = _normalize(res)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(to_plain_json(data), output=cfg.output, fields=cfg.fields, jq=cfg.jq)


@users_app.command("show")
def show_user(
    id: str,
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
    as_dict: Annotated[
        Optional[str],
        typer.Option(None, "--as-dict", metavar="BOOL", help="true/false. Omit to use Settings.return_models default."),
    ] = None,
) -> None:
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
        as_dict=parse_bool_opt(as_dict),
    )
    settings = make_settings(cfg)

    try:
        if cfg.engine == "async":

            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.get(f"{API_PATH}/{id}")

            data = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                data = client.get(f"{API_PATH}/{id}")
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(to_plain_json(data), output=cfg.output, fields=[], jq=cfg.jq)
