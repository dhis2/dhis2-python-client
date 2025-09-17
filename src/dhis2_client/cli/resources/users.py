from __future__ import annotations

import sys
from typing import Annotated, Any, Dict, Optional, TYPE_CHECKING, List  # Literal removed

import typer
from click import Choice  # <-- for validated choices

from ..common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from ..output import render_output
from ..utils import parse_bool_opt, to_plain_json

if TYPE_CHECKING:
    from dhis2_client import DHIS2Client, DHIS2AsyncClient

users_app = typer.Typer(help="Users")

API_PATH = "/api/users"
ARRAY_KEY = "users"
DEFAULT_FIELDS = ["id", "username", "displayName", "email"]


def _normalize(res: Dict[str, Any]) -> List[dict]:
    return res.get(ARRAY_KEY, []) if isinstance(res, dict) else []


async def _async_list_all_users(
    client: "DHIS2AsyncClient",
    page_size: Optional[int],
    fields_csv: str,
) -> List[dict]:
    # always request paging for predictable structure
    first = await client.get(API_PATH, params={"paging": True, "pageSize": page_size, "page": 1, "fields": fields_csv})
    items: List[dict] = _normalize(first)
    pager = int(first.get("pager", {}).get("pageCount", 1)) if isinstance(first, dict) else 1
    for p in range(2, pager + 1):
        res = await client.get(
            API_PATH, params={"paging": True, "pageSize": page_size, "page": p, "fields": fields_csv}
        )
        items.extend(_normalize(res))
    return items


def _sync_list_all_users(
    client: "DHIS2Client",
    page_size: Optional[int],
    fields_csv: str,
) -> List[dict]:
    first = client.get(API_PATH, params={"paging": True, "pageSize": page_size, "page": 1, "fields": fields_csv})
    items: List[dict] = _normalize(first)
    pager = int(first.get("pager", {}).get("pageCount", 1)) if isinstance(first, dict) else 1
    for p in range(2, pager + 1):
        res = client.get(
            API_PATH, params={"paging": True, "pageSize": page_size, "page": p, "fields": fields_csv}
        )
        items.extend(_normalize(res))
    return items


@users_app.command("list")
def list_users(
    base_url: Annotated[Optional[str], typer.Option("--base-url")] = None,
    username: Annotated[Optional[str], typer.Option("--username")] = None,
    password: Annotated[Optional[str], typer.Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    password_stdin: Annotated[bool, typer.Option("--password-stdin", is_flag=True)] = False,
    engine: Annotated[
        str,
        typer.Option(
            "--engine",
            click_type=Choice(["sync", "async"], case_sensitive=False),
            help="sync|async (default: sync)",
        ),
    ] = "sync",
    profile: Annotated[Optional[str], typer.Option("--profile")] = None,
    page_size: Annotated[Optional[int], typer.Option("--page-size")] = None,
    all_pages: Annotated[bool, typer.Option("--all", is_flag=True, help="Fetch all pages")] = False,
    fields: Annotated[List[str], typer.Option("--fields")] = DEFAULT_FIELDS.copy(),
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            click_type=Choice(["table", "json", "yaml"], case_sensitive=False),
            help="table|json|yaml (default: table)",
        ),
    ] = "table",
    jq: Annotated[Optional[str], typer.Option("--jq")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
    as_dict: Annotated[
        Optional[str],
        typer.Option("--as-dict", metavar="BOOL", help="true/false. Omit to use Settings.return_models default.")
    ] = None,
) -> None:
    # Password handling
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    # Build CLI + Settings
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
        fields=fields,
        jq=jq,
        profile=profile,
        page_size=page_size,
        all_pages=all_pages,
        password_stdin=password_stdin,
        array_key=ARRAY_KEY,
        as_dict=parse_bool_opt(as_dict),
    )
    settings = make_settings(cfg)
    query_fields = ",".join(fields) if fields else ",".join(DEFAULT_FIELDS)

    try:
        if cfg.engine == "async":
            from dhis2_client import DHIS2AsyncClient

            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    if cfg.all_pages:
                        return await _async_list_all_users(client, cfg.page_size, query_fields)
                    # single page (for predictability, still request paging)
                    res = await client.get(
                        API_PATH, params={"paging": True, "pageSize": cfg.page_size, "page": 1, "fields": query_fields}
                    )
                    return _normalize(res)

            data = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                if cfg.all_pages:
                    data = _sync_list_all_users(client, cfg.page_size, query_fields)
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
    id: Annotated[str, typer.Argument(..., help="User UID")],
    base_url: Annotated[Optional[str], typer.Option("--base-url")] = None,
    username: Annotated[Optional[str], typer.Option("--username")] = None,
    password: Annotated[Optional[str], typer.Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    password_stdin: Annotated[bool, typer.Option("--password-stdin", is_flag=True)] = False,
    engine: Annotated[
        str,
        typer.Option(
            "--engine",
            click_type=Choice(["sync", "async"], case_sensitive=False),
            help="sync|async (default: sync)",
        ),
    ] = "sync",
    profile: Annotated[Optional[str], typer.Option("--profile")] = None,
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            click_type=Choice(["table", "json", "yaml"], case_sensitive=False),
            help="table|json|yaml (default: json)",
        ),
    ] = "json",
    jq: Annotated[Optional[str], typer.Option("--jq")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
    as_dict: Annotated[
        Optional[str],
        typer.Option("--as-dict", metavar="BOOL", help="true/false. Omit to use Settings.return_models default.")
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
        engine=engine.lower(),
        output=output.lower(),
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
            from dhis2_client import DHIS2AsyncClient

            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.get(f"{API_PATH}/{id}")

            data = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                data = client.get(f"{API_PATH}/{id}")
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(to_plain_json(data), output=cfg.output, fields=[], jq=cfg.jq)
