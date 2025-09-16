from __future__ import annotations
import sys
from typing import Optional, Dict, Any
import typer

from ..common import resolve_settings, make_settings, run_async, CLISettings, print_http_error
from ..output import render_output
from dhis2_client import DHIS2AsyncClient, DHIS2Client

users_app = typer.Typer(help="Users")

API_PATH = "/api/users"
ARRAY_KEY = "users"
DEFAULT_FIELDS = ["id", "username", "displayName", "email"]


def _normalize(res: Dict[str, Any]) -> list[dict]:
    return res.get(ARRAY_KEY, []) if isinstance(res, dict) else []


@users_app.command("list")
def list_users(
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    username: Optional[str] = typer.Option(None, "--username"),
    password: Optional[str] = typer.Option(None, "--password", prompt=False, hide_input=True),
    token: Optional[str] = typer.Option(None, "--token"),
    password_stdin: bool = typer.Option(False, "--password-stdin"),
    engine: Optional[str] = typer.Option(None, "--engine", help="sync|async"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    page_size: Optional[int] = typer.Option(None, "--page-size"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages"),
    fields: list[str] = typer.Option(DEFAULT_FIELDS, "--fields"),
    output: Optional[str] = typer.Option("table", "--output"),
    jq: Optional[str] = typer.Option(None, "--jq"),
    verbose: bool = typer.Option(False, "--verbose", help="Show full error details on failure."),
) -> None:
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg: CLISettings = resolve_settings(
        base_url=base_url, username=username, password=pw, token=token,
        timeout=None, verify_ssl=None, log_level=None,
        engine=engine, output=output, fields=fields, jq=jq, profile=profile,
        page_size=page_size, all_pages=all_pages, password_stdin=password_stdin, array_key=ARRAY_KEY,
    )
    settings = make_settings(cfg)
    query_fields = ",".join(fields) if fields else ",".join(DEFAULT_FIELDS)

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    if cfg.all_pages:
                        items: list[dict] = []
                        first = await client.get(API_PATH, params={"paging": True, "pageSize": cfg.page_size, "page": 1, "fields": query_fields})
                        pager = int(first.get("pager", {}).get("pageCount", 1)) if isinstance(first, dict) else 1
                        items.extend(_normalize(first))
                        for p in range(2, pager + 1):
                            res = await client.get(API_PATH, params={"paging": True, "pageSize": cfg.page_size, "page": p, "fields": query_fields})
                            items.extend(_normalize(res))
                        return items
                    res = await client.get(API_PATH, params={"paging": True, "pageSize": cfg.page_size, "page": 1, "fields": query_fields})
                    return _normalize(res)
            data = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                if cfg.all_pages:
                    items: list[dict] = []
                    first = client.get(API_PATH, params={"paging": True, "pageSize": cfg.page_size, "page": 1, "fields": query_fields})
                    pager = int(first.get("pager", {}).get("pageCount", 1)) if isinstance(first, dict) else 1
                    items.extend(_normalize(first))
                    for p in range(2, pager + 1):
                        res = client.get(API_PATH, params={"paging": True, "pageSize": cfg.page_size, "page": p, "fields": query_fields})
                        items.extend(_normalize(res))
                    data = items
                else:
                    res = client.get(API_PATH, params={"paging": True, "pageSize": cfg.page_size, "page": 1, "fields": query_fields})
                    data = _normalize(res)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(data, output=cfg.output, fields=cfg.fields, jq=cfg.jq)


@users_app.command("show")
def show_user(
    id: str,
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
) -> None:
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
        raise typer.Exit(code=4)

    render_output(data, output=cfg.output, fields=[], jq=cfg.jq)


@users_app.command("create")
def create_user(
    json_body: str = typer.Option(..., "--json", help="Raw JSON or @file.json"),
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
) -> None:
    from ..http import _load_json_arg  # reuse
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)
    payload = _load_json_arg(json_body)

    cfg: CLISettings = resolve_settings(
        base_url=base_url, username=username, password=pw, token=token,
        timeout=None, verify_ssl=None, log_level=None,
        engine=engine, output=output, fields=[], jq=jq, profile=profile,
        page_size=None, all_pages=False, password_stdin=password_stdin, array_key=None
    )
    settings = make_settings(cfg)

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.post_json(API_PATH, payload=payload)
            res = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                res = client.post_json(API_PATH, payload=payload)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)


@users_app.command("update")
def update_user(
    id: str,
    json_body: str = typer.Option(..., "--json", help="Raw JSON or @file.json"),
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
) -> None:
    from ..http import _load_json_arg
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)
    payload = _load_json_arg(json_body)

    cfg: CLISettings = resolve_settings(
        base_url=base_url, username=username, password=pw, token=token,
        timeout=None, verify_ssl=None, log_level=None,
        engine=engine, output=output, fields=[], jq=jq, profile=profile,
        page_size=None, all_pages=False, password_stdin=password_stdin, array_key=None
    )
    settings = make_settings(cfg)

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.put_json(f"{API_PATH}/{id}", payload=payload)
            res = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                res = client.put_json(f"{API_PATH}/{id}", payload=payload)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)


@users_app.command("delete")
def delete_user(
    id: str,
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
) -> None:
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

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.delete(f"{API_PATH}/{id}")
            res = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                res = client.delete(f"{API_PATH}/{id}")
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)
