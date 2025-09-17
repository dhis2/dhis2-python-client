from __future__ import annotations

import sys
from typing import Annotated, Any, Dict, Optional, TYPE_CHECKING, Iterable, List  # Literal removed

import typer
from click import Choice  # <-- robust value validation

from .common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from .output import render_output
from .utils import detect_array_key, load_json_arg, parse_bool_opt, parse_params, to_plain_json

if TYPE_CHECKING:
    from dhis2_client import DHIS2Client, DHIS2AsyncClient

http_app = typer.Typer(help="Generic HTTP helpers")
Option = typer.Option
Argument = typer.Argument


# ---------------------------
# helpers (unchanged logic)
# ---------------------------
async def _async_get_all(
    client: "DHIS2AsyncClient",
    path: str,
    params: Dict[str, Any],
    page_size: int,
    array_key: Optional[str],
):
    first = await client.get(path, params={**params, "paging": True, "pageSize": page_size, "page": 1})
    if not isinstance(first, dict) or "pager" not in first:
        return first
    key = array_key or detect_array_key(first) or "items"
    items = list(first.get(key, []))
    page_count = int(first.get("pager", {}).get("pageCount", 1))
    for page in range(2, page_count + 1):
        res = await client.get(path, params={**params, "paging": True, "pageSize": page_size, "page": page})
        items.extend(res.get(key, []))
    return items


def _sync_get_all(
    client: "DHIS2Client",
    path: str,
    params: Dict[str, Any],
    page_size: int,
    array_key: Optional[str],
):
    first = client.get(path, params={**params, "paging": True, "pageSize": page_size, "page": 1})
    if not isinstance(first, dict) or "pager" not in first:
        return first
    key = array_key or detect_array_key(first) or "items"
    items = list(first.get(key, []))
    page_count = int(first.get("pager", {}).get("pageCount", 1))
    for page in range(2, page_count + 1):
        res = client.get(path, params={**params, "paging": True, "pageSize": page_size, "page": page})
        items.extend(res.get(key, []))
    return items


# ---------------------------
# GET
# ---------------------------
@http_app.command("get")
def get(
    path: Annotated[str, Argument(..., help="e.g. /api/users")],
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True, help="Prefer prompt/STDIN.")] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    timeout: Annotated[Optional[float], Option("--timeout")] = None,
    verify_ssl: Annotated[Optional[bool], Option("--verify-ssl/--insecure")] = None,
    log_level: Annotated[
        Optional[str],
        Option(
            "--log-level",
            click_type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
            help="DEBUG|INFO|WARNING|ERROR|CRITICAL",
        ),
    ] = None,
    engine: Annotated[
        str,
        Option(
            "--engine",
            click_type=Choice(["sync", "async"], case_sensitive=False),
            help="sync|async (default: sync)",
        ),
    ] = "sync",
    output: Annotated[
        str,
        Option(
            "--output",
            "-o",
            click_type=Choice(["table", "json", "yaml"], case_sensitive=False),
            help="table|json|yaml (default: json)",
        ),
    ] = "json",
    field: Annotated[list[str], Option("--fields", help="Repeatable: --fields id --fields name")] = [],
    jq: Annotated[Optional[str], Option("--jq")] = None,
    profile: Annotated[Optional[str], Option("--profile")] = None,
    page_size: Annotated[Optional[int], Option("--page-size")] = None,
    all_pages: Annotated[bool, Option("--all", is_flag=True, help="Iterate all pages via pager.")] = False,
    array_key: Annotated[Optional[str], Option("--array-key", help="Collection key (e.g., users)")] = None,
    param: Annotated[list[str], Option("--param", help="Query key=value (repeatable)")] = [],
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
    as_dict: Annotated[
        Optional[str],
        Option("--as-dict", metavar="BOOL", help="true/false. Omit to use the default from Settings.return_models.")
    ] = None,
) -> None:
    # password handling
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
        log_level=(log_level.upper() if log_level else None),
        engine=engine.lower(),
        output=output.lower(),
        fields=field,
        jq=jq,
        profile=profile,
        page_size=page_size,
        all_pages=all_pages,
        password_stdin=password_stdin,
        array_key=array_key,
        as_dict=parse_bool_opt(as_dict),
    )
    settings = make_settings(cfg)
    params = parse_params(param)

    try:
        if cfg.engine == "async":
            from dhis2_client import DHIS2AsyncClient
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    if cfg.all_pages and cfg.page_size:
                        return await _async_get_all(client, path, params, cfg.page_size, cfg.array_key)
                    return await client.get(path, params=params)
            data = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                if cfg.all_pages and cfg.page_size:
                    data = _sync_get_all(client, path, params, cfg.page_size, cfg.array_key)
                else:
                    data = client.get(path, params=params)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(to_plain_json(data), output=cfg.output, fields=cfg.fields, jq=cfg.jq)


# ---------------------------
# POST
# ---------------------------
@http_app.command("post")
def post(
    path: Annotated[str, Argument(..., help="e.g. /api/dataElements")],
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    timeout: Annotated[Optional[float], Option("--timeout")] = None,
    verify_ssl: Annotated[Optional[bool], Option("--verify-ssl/--insecure")] = None,
    log_level: Annotated[
        Optional[str],
        Option(
            "--log-level",
            click_type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
            help="DEBUG|INFO|WARNING|ERROR|CRITICAL",
        ),
    ] = None,
    engine: Annotated[
        str,
        Option(
            "--engine",
            click_type=Choice(["sync", "async"], case_sensitive=False),
            help="sync|async (default: sync)",
        ),
    ] = "sync",
    output: Annotated[
        str,
        Option(
            "--output",
            "-o",
            click_type=Choice(["table", "json", "yaml"], case_sensitive=False),
            help="table|json|yaml (default: json)",
        ),
    ] = "json",
    field: Annotated[list[str], Option("--fields")] = [],
    jq: Annotated[Optional[str], Option("--jq")] = None,
    profile: Annotated[Optional[str], Option("--profile")] = None,
    json_body: Annotated[Optional[str], Option("--json", help="Raw JSON or @file.json")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
    as_dict: Annotated[Optional[str], Option("--as-dict", metavar="BOOL", help="true/false. Use Settings default if omitted.")] = None,
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
        log_level=(log_level.upper() if log_level else None),
        engine=engine.lower(),
        output=output.lower(),
        fields=field,
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
        as_dict=parse_bool_opt(as_dict),
    )
    settings = make_settings(cfg)
    payload = load_json_arg(json_body)

    try:
        if cfg.engine == "async":
            from dhis2_client import DHIS2AsyncClient
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.post_json(path, payload=payload)
            res = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                res = client.post_json(path, payload=payload)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(to_plain_json(res), output=cfg.output, fields=cfg.fields, jq=cfg.jq)


# ---------------------------
# PUT
# ---------------------------
@http_app.command("put")
def put(
    path: Annotated[str, Argument(..., help="e.g. /api/dataElements/ID")],
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    timeout: Annotated[Optional[float], Option("--timeout")] = None,
    verify_ssl: Annotated[Optional[bool], Option("--verify-ssl/--insecure")] = None,
    log_level: Annotated[
        Optional[str],
        Option(
            "--log-level",
            click_type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
            help="DEBUG|INFO|WARNING|ERROR|CRITICAL",
        ),
    ] = None,
    engine: Annotated[
        str,
        Option(
            "--engine",
            click_type=Choice(["sync", "async"], case_sensitive=False),
            help="sync|async (default: sync)",
        ),
    ] = "sync",
    output: Annotated[
        str,
        Option(
            "--output",
            "-o",
            click_type=Choice(["table", "json", "yaml"], case_sensitive=False),
            help="table|json|yaml (default: json)",
        ),
    ] = "json",
    field: Annotated[list[str], Option("--fields")] = [],
    jq: Annotated[Optional[str], Option("--jq")] = None,
    profile: Annotated[Optional[str], Option("--profile")] = None,
    json_body: Annotated[Optional[str], Option("--json", help="Raw JSON or @file.json")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
    as_dict: Annotated[Optional[str], Option("--as-dict", metavar="BOOL", help="true/false. Use Settings default if omitted.")] = None,
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
        log_level=(log_level.upper() if log_level else None),
        engine=engine.lower(),
        output=output.lower(),
        fields=field,
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
        as_dict=parse_bool_opt(as_dict),
    )
    settings = make_settings(cfg)
    payload = load_json_arg(json_body)

    try:
        if cfg.engine == "async":
            from dhis2_client import DHIS2AsyncClient
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.put_json(path, payload=payload)
            res = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                res = client.put_json(path, payload=payload)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(to_plain_json(res), output=cfg.output, fields=cfg.fields, jq=cfg.jq)


# ---------------------------
# DELETE
# ---------------------------
@http_app.command("delete")
def delete(
    path: Annotated[str, Argument(..., help="e.g. /api/dataElements/ID")],
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    timeout: Annotated[Optional[float], Option("--timeout")] = None,
    verify_ssl: Annotated[Optional[bool], Option("--verify-ssl/--insecure")] = None,
    log_level: Annotated[
        Optional[str],
        Option(
            "--log-level",
            click_type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
            help="DEBUG|INFO|WARNING|ERROR|CRITICAL",
        ),
    ] = None,
    engine: Annotated[
        str,
        Option(
            "--engine",
            click_type=Choice(["sync", "async"], case_sensitive=False),
            help="sync|async (default: sync)",
        ),
    ] = "sync",
    output: Annotated[
        str,
        Option(
            "--output",
            "-o",
            click_type=Choice(["table", "json", "yaml"], case_sensitive=False),
            help="table|json|yaml (default: json)",
        ),
    ] = "json",
    field: Annotated[list[str], Option("--fields")] = [],
    jq: Annotated[Optional[str], Option("--jq")] = None,
    profile: Annotated[Optional[str], Option("--profile")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
    as_dict: Annotated[Optional[str], Option("--as-dict", metavar="BOOL", help="true/false. Use Settings default if omitted.")] = None,
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
        log_level=(log_level.upper() if log_level else None),
        engine=engine.lower(),
        output=output.lower(),
        fields=field,
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
            from dhis2_client import DHIS2AsyncClient
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.delete(path)
            res = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                res = client.delete(path)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(to_plain_json(res), output=cfg.output, fields=cfg.fields, jq=cfg.jq)
