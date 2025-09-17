from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path
from typing import Annotated, Any, Dict, Optional, TYPE_CHECKING, List, Literal
from urllib.parse import urlencode

import typer
from click import Choice  # <- enum-like validation for Typer

from ..common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from ..output import render_output

if TYPE_CHECKING:
    from dhis2_client import DHIS2Client, DHIS2AsyncClient

bulk_app = typer.Typer(help="Generic bulk JSON sender (POST/PUT/PATCH to any /api/* path)")

Option = typer.Option
Argument = typer.Argument


def _read_json(source: str):
    if source == "-":
        return json.loads(sys.stdin.read())
    if source.startswith("@"):
        p = Path(source[1:])
        data = p.read_bytes()
        if p.suffix == ".gz":
            data = gzip.decompress(data)
        return json.loads(data.decode("utf-8"))
    return json.loads(source)


def _parse_params(items: List[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for it in items:
        if "=" not in it:
            raise typer.BadParameter(f"Invalid --param '{it}', expected key=value")
        k, v = it.split("=", 1)
        params[k] = v
    return params


def _send(
    method: Literal["POST", "PUT", "PATCH"],
    path: str,
    payload: Any,
    cfg: CLISettings,
    settings,
):
    if cfg.engine == "async":
        from dhis2_client import DHIS2AsyncClient

        async def _run():
            async with DHIS2AsyncClient.from_settings(settings) as client:
                if method == "POST":
                    return await client.post_json(path, payload=payload)
                if method == "PUT":
                    return await client.put_json(path, payload=payload)
                if hasattr(client, "patch_json"):
                    return await client.patch_json(path, payload=payload)  # type: ignore[attr-defined]
                raise typer.BadParameter("Async client has no patch_json()")
        return run_async(_run())
    else:
        from dhis2_client import DHIS2Client
        with DHIS2Client.from_settings(settings) as client:
            if method == "POST":
                return client.post_json(path, payload=payload)
            if method == "PUT":
                return client.put_json(path, payload=payload)
            if hasattr(client, "patch_json"):
                return client.patch_json(path, payload=payload)  # type: ignore[attr-defined]
            raise typer.BadParameter("Sync client has no patch_json()")


def _common(
    method: Literal["POST", "PUT", "PATCH"],
    path: str,
    source: str,
    base_url: Optional[str],
    username: Optional[str],
    password: Optional[str],
    token: Optional[str],
    password_stdin: bool,
    engine: str,
    profile: Optional[str],
    output: str,
    jq: Optional[str],
    params_kv: List[str],
    verbose: bool,
):
    if not path.startswith("/api/"):
        raise typer.BadParameter("Path must start with /api/ ...")

    payload = _read_json(source)

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
        engine=(engine or "sync").lower(),
        output=(output or "json").lower(),
        fields=[],
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
    )
    settings = make_settings(cfg)

    params = _parse_params(params_kv)
    path_q = f"{path}?{urlencode(params, doseq=True)}" if params else path

    try:
        res = _send(method, path_q, payload, cfg, settings)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)


@bulk_app.command("post")
def post(
    path: Annotated[str, Argument(..., help="Absolute API path, e.g. /api/events")],
    source: Annotated[str, Option("--source", help="JSON text, @file.json, @file.json.gz, or '-' for stdin")],
    param: Annotated[List[str], Option("--param", help="Query params key=value")] = [],
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    engine: Annotated[
        str, Option("--engine", click_type=Choice(["sync", "async"], case_sensitive=False), help="Default: sync")
    ] = "sync",
    profile: Annotated[Optional[str], Option("--profile")] = None,
    output: Annotated[
        str, Option("--output", "-o", click_type=Choice(["table", "json", "yaml"], case_sensitive=False))
    ] = "json",
    jq: Annotated[Optional[str], Option("--jq")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
):
    _common(
        "POST",
        path,
        source,
        base_url,
        username,
        password,
        token,
        password_stdin,
        engine,
        profile,
        output,
        jq,
        param,
        verbose,
    )


@bulk_app.command("put")
def put(
    path: Annotated[str, Argument(..., help="Absolute API path, e.g. /api/events/ID")],
    source: Annotated[str, Option("--source", help="JSON text, @file.json, @file.json.gz, or '-' for stdin")],
    param: Annotated[List[str], Option("--param", help="Query params key=value")] = [],
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    engine: Annotated[
        str, Option("--engine", click_type=Choice(["sync", "async"], case_sensitive=False), help="Default: sync")
    ] = "sync",
    profile: Annotated[Optional[str], Option("--profile")] = None,
    output: Annotated[
        str, Option("--output", "-o", click_type=Choice(["table", "json", "yaml"], case_sensitive=False))
    ] = "json",
    jq: Annotated[Optional[str], Option("--jq")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
):
    _common(
        "PUT",
        path,
        source,
        base_url,
        username,
        password,
        token,
        password_stdin,
        engine,
        profile,
        output,
        jq,
        param,
        verbose,
    )


@bulk_app.command("patch")
def patch(
    path: Annotated[str, Argument(..., help="Absolute API path, e.g. /api/events/ID")],
    source: Annotated[str, Option("--source", help="JSON text, @file.json, @file.json.gz, or '-' for stdin")],
    param: Annotated[List[str], Option("--param", help="Query params key=value")] = [],
    base_url: Annotated[Optional[str], Option("--base-url")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[Optional[str], Option("--password", prompt=False, hide_input=True)] = None,
    token: Annotated[Optional[str], Option("--token")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True)] = False,
    engine: Annotated[
        str, Option("--engine", click_type=Choice(["sync", "async"], case_sensitive=False), help="Default: sync")
    ] = "sync",
    profile: Annotated[Optional[str], Option("--profile")] = None,
    output: Annotated[
        str, Option("--output", "-o", click_type=Choice(["table", "json", "yaml"], case_sensitive=False))
    ] = "json",
    jq: Annotated[Optional[str], Option("--jq")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,
):
    _common(
        "PATCH",
        path,
        source,
        base_url,
        username,
        password,
        token,
        password_stdin,
        engine,
        profile,
        output,
        jq,
        param,
        verbose,
    )
