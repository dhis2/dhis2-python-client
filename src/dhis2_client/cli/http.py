from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import typer

from dhis2_client import DHIS2AsyncClient, DHIS2Client

from .common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from .output import render_output

http_app = typer.Typer(help="Generic HTTP helpers")


def _parse_params(items: list[str]) -> dict:
    params: Dict[str, str] = {}
    for p in items:
        if "=" not in p:
            raise typer.BadParameter(f"Invalid --param '{p}', expected key=value")
        k, v = p.split("=", 1)
        params[k] = v
    return params


def _load_json_arg(json_arg: Optional[str]) -> object | None:
    if not json_arg:
        return None
    if json_arg.startswith("@"):
        p = Path(json_arg[1:])
        return json.loads(p.read_text(encoding="utf-8"))
    return json.loads(json_arg)


def _detect_array_key(obj: Dict[str, Any]) -> Optional[str]:
    # Heuristic: first list-of-dicts key
    for k, v in obj.items():
        if isinstance(v, list) and (not v or isinstance(v[0], dict)):
            return k
    return None


async def _async_get_all(
    client: DHIS2AsyncClient,
    path: str,
    params: Dict[str, Any],
    page_size: int,
    array_key: Optional[str],
):
    first = await client.get(
        path, params={**params, "paging": True, "pageSize": page_size, "page": 1}
    )
    if not isinstance(first, dict) or "pager" not in first:
        return first
    key = array_key or _detect_array_key(first) or "items"
    items = list(first.get(key, []))
    page_count = int(first.get("pager", {}).get("pageCount", 1))
    for page in range(2, page_count + 1):
        res = await client.get(
            path, params={**params, "paging": True, "pageSize": page_size, "page": page}
        )
        items.extend(res.get(key, []))
    return items


def _sync_get_all(
    client: DHIS2Client,
    path: str,
    params: Dict[str, Any],
    page_size: int,
    array_key: Optional[str],
):
    first = client.get(
        path, params={**params, "paging": True, "pageSize": page_size, "page": 1}
    )
    if not isinstance(first, dict) or "pager" not in first:
        return first
    key = array_key or _detect_array_key(first) or "items"
    items = list(first.get(key, []))
    page_count = int(first.get("pager", {}).get("pageCount", 1))
    for page in range(2, page_count + 1):
        res = client.get(
            path, params={**params, "paging": True, "pageSize": page_size, "page": page}
        )
        items.extend(res.get(key, []))
    return items


@http_app.command("get")
def get(
    path: str = typer.Argument(..., help="e.g. /api/users"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    username: Optional[str] = typer.Option(None, "--username"),
    password: Optional[str] = typer.Option(
        None, "--password", prompt=False, hide_input=True, help="Prefer prompt/STDIN."
    ),
    token: Optional[str] = typer.Option(None, "--token"),
    password_stdin: bool = typer.Option(False, "--password-stdin"),
    timeout: Optional[float] = typer.Option(None, "--timeout"),
    verify_ssl: Optional[bool] = typer.Option(None, "--verify-ssl/--insecure"),
    log_level: Optional[str] = typer.Option(None, "--log-level"),
    engine: Optional[str] = typer.Option(None, "--engine", help="sync|async"),
    output: Optional[str] = typer.Option("table", "--output"),
    field: list[str] = typer.Option([], "--fields"),
    jq: Optional[str] = typer.Option(None, "--jq"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    page_size: Optional[int] = typer.Option(None, "--page-size"),
    all_pages: bool = typer.Option(False, "--all", help="Iterate all pages via pager."),
    array_key: Optional[str] = typer.Option(None, "--array-key", help="Collection key (e.g., users)"),
    param: list[str] = typer.Option([], "--param", help="Query key=value"),
    verbose: bool = typer.Option(False, "--verbose", help="Show full error details on failure."),
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
        timeout=timeout,
        verify_ssl=verify_ssl,
        log_level=log_level,
        engine=engine,
        output=output,
        fields=field,
        jq=jq,
        profile=profile,
        page_size=page_size,
        all_pages=all_pages,
        password_stdin=password_stdin,
        array_key=array_key,
    )
    settings = make_settings(cfg)
    params = _parse_params(param)

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    if cfg.all_pages:
                        return await _async_get_all(client, path, params, cfg.page_size, cfg.array_key)
                    return await client.get(path, params=params)
            data = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                if cfg.all_pages:
                    data = _sync_get_all(client, path, params, cfg.page_size, cfg.array_key)
                else:
                    data = client.get(path, params=params)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(data, output=cfg.output, fields=cfg.fields, jq=cfg.jq)


@http_app.command("post")
def post(
    path: str,
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    username: Optional[str] = typer.Option(None, "--username"),
    password: Optional[str] = typer.Option(None, "--password", prompt=False, hide_input=True),
    token: Optional[str] = typer.Option(None, "--token"),
    password_stdin: bool = typer.Option(False, "--password-stdin"),
    timeout: Optional[float] = typer.Option(None, "--timeout"),
    verify_ssl: Optional[bool] = typer.Option(None, "--verify-ssl/--insecure"),
    log_level: Optional[str] = typer.Option(None, "--log-level"),
    engine: Optional[str] = typer.Option(None, "--engine", help="sync|async"),
    output: Optional[str] = typer.Option("table", "--output"),
    field: list[str] = typer.Option([], "--fields"),
    jq: Optional[str] = typer.Option(None, "--jq"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    json_body: Optional[str] = typer.Option(None, "--json", help="Raw JSON or @file.json"),
    verbose: bool = typer.Option(False, "--verbose", help="Show full error details on failure."),
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
        timeout=timeout,
        verify_ssl=verify_ssl,
        log_level=log_level,
        engine=engine,
        output=output,
        fields=field,
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
    )
    settings = make_settings(cfg)
    payload = _load_json_arg(json_body)

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.post_json(path, payload=payload)
            res = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                res = client.post_json(path, payload=payload)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(res, output=cfg.output, fields=cfg.fields, jq=cfg.jq)


@http_app.command("put")
def put(
    path: str,
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    username: Optional[str] = typer.Option(None, "--username"),
    password: Optional[str] = typer.Option(None, "--password", prompt=False, hide_input=True),
    token: Optional[str] = typer.Option(None, "--token"),
    password_stdin: bool = typer.Option(False, "--password-stdin"),
    timeout: Optional[float] = typer.Option(None, "--timeout"),
    verify_ssl: Optional[bool] = typer.Option(None, "--verify-ssl/--insecure"),
    log_level: Optional[str] = typer.Option(None, "--log-level"),
    engine: Optional[str] = typer.Option(None, "--engine", help="sync|async"),
    output: Optional[str] = typer.Option("table", "--output"),
    field: list[str] = typer.Option([], "--fields"),
    jq: Optional[str] = typer.Option(None, "--jq"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    json_body: Optional[str] = typer.Option(None, "--json", help="Raw JSON or @file.json"),
    verbose: bool = typer.Option(False, "--verbose", help="Show full error details on failure."),
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
        timeout=timeout,
        verify_ssl=verify_ssl,
        log_level=log_level,
        engine=engine,
        output=output,
        fields=field,
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
    )
    settings = make_settings(cfg)
    payload = _load_json_arg(json_body)

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.put_json(path, payload=payload)
            res = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                res = client.put_json(path, payload=payload)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(res, output=cfg.output, fields=cfg.fields, jq=cfg.jq)


@http_app.command("delete")
def delete(
    path: str,
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    username: Optional[str] = typer.Option(None, "--username"),
    password: Optional[str] = typer.Option(None, "--password", prompt=False, hide_input=True),
    token: Optional[str] = typer.Option(None, "--token"),
    password_stdin: bool = typer.Option(False, "--password-stdin"),
    timeout: Optional[float] = typer.Option(None, "--timeout"),
    verify_ssl: Optional[bool] = typer.Option(None, "--verify-ssl/--insecure"),
    log_level: Optional[str] = typer.Option(None, "--log-level"),
    engine: Optional[str] = typer.Option(None, "--engine", help="sync|async"),
    output: Optional[str] = typer.Option("table", "--output"),
    field: list[str] = typer.Option([], "--fields"),
    jq: Optional[str] = typer.Option(None, "--jq"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    verbose: bool = typer.Option(False, "--verbose", help="Show full error details on failure."),
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
        timeout=timeout,
        verify_ssl=verify_ssl,
        log_level=log_level,
        engine=engine,
        output=output,
        fields=field,
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
    )
    settings = make_settings(cfg)

    try:
        if cfg.engine == "async":
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.delete(path)
            res = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                res = client.delete(path)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(res, output=cfg.output, fields=cfg.fields, jq=cfg.jq)
