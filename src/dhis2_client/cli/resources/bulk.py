from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from urllib.parse import urlencode

import typer
from dhis2_client import DHIS2AsyncClient, DHIS2Client

from ..common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from ..output import render_output

bulk_app = typer.Typer(help="Generic bulk JSON sender (POST/PUT/PATCH to any /api/* path)")

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

def _parse_params(items: list[str]) -> Dict[str, str]:
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
        async def _run():
            async with DHIS2AsyncClient.from_settings(settings) as client:
                if method == "POST":
                    return await client.post_json(path, payload=payload)
                if method == "PUT":
                    return await client.put_json(path, payload=payload)
                # PATCH (if your client supports it; otherwise fallback to put_json or raise)
                if hasattr(client, "patch_json"):
                    return await client.patch_json(path, payload=payload)  # type: ignore
                raise typer.BadParameter("Async client has no patch_json()")
        return run_async(_run())
    else:
        with DHIS2Client.from_settings(settings) as client:
            if method == "POST":
                return client.post_json(path, payload=payload)
            if method == "PUT":
                return client.put_json(path, payload=payload)
            if hasattr(client, "patch_json"):
                return client.patch_json(path, payload=payload)  # type: ignore
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
    engine: Optional[str],
    profile: Optional[str],
    output: Optional[str],
    jq: Optional[str],
    params_kv: list[str],
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
        base_url=base_url, username=username, password=pw, token=token,
        timeout=None, verify_ssl=None, log_level=None,
        engine=engine, output=output or "json", fields=[], jq=jq, profile=profile,
        page_size=None, all_pages=False, password_stdin=password_stdin, array_key=None
    )
    settings = make_settings(cfg)

    params = _parse_params(params_kv)
    path_q = f"{path}?{urlencode(params, doseq=True)}" if params else path

    try:
        res = _send(method, path_q, payload, cfg, settings)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)

@bulk_app.command("post")
def post(
    path: str = typer.Argument(..., help="Absolute API path, e.g. /api/events"),
    source: str = typer.Option(..., "--source", help="JSON text, @file.json, @file.json.gz, or '-' for stdin"),
    param: list[str] = typer.Option([], "--param", help="Query params key=value"),
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
    _common("POST", path, source, base_url, username, password, token, password_stdin, engine, profile, output, jq, param, verbose)

@bulk_app.command("put")
def put(
    path: str = typer.Argument(..., help="Absolute API path, e.g. /api/events/ID"),
    source: str = typer.Option(..., "--source", help="JSON text, @file.json, @file.json.gz, or '-' for stdin"),
    param: list[str] = typer.Option([], "--param", help="Query params key=value"),
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
    _common("PUT", path, source, base_url, username, password, token, password_stdin, engine, profile, output, jq, param, verbose)

@bulk_app.command("patch")
def patch(
    path: str = typer.Argument(..., help="Absolute API path, e.g. /api/events/ID"),
    source: str = typer.Option(..., "--source", help="JSON text, @file.json, @file.json.gz, or '-' for stdin"),
    param: list[str] = typer.Option([], "--param", help="Query params key=value"),
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
    _common("PATCH", path, source, base_url, username, password, token, password_stdin, engine, profile, output, jq, param, verbose)
