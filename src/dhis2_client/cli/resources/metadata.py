from __future__ import annotations

import sys
from typing import Annotated, Any, Dict, List, Optional

import typer
from dhis2_client import DHIS2AsyncClient, DHIS2Client

from ..common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from ..output import render_output

metadata_app = typer.Typer(help="Generic metadata operations for any DHIS2 collection")


def _normalize_collection(res: Dict[str, Any], array_key: Optional[str]) -> list[dict]:
    if isinstance(res, dict):
        if array_key and array_key in res and isinstance(res[array_key], list):
            return res[array_key]
        for _k, v in res.items():
            if isinstance(v, list) and (not v or isinstance(v[0], dict)):
                return v
    return res if isinstance(res, list) else [res]


def _parse_filters(filters: List[str]) -> List[str]:
    out: List[str] = []
    for f in filters:
        parts = f.split(":", 2)
        if len(parts) < 3:
            raise typer.BadParameter(f"Invalid --filter '{f}'. Expected key:op:value")
        out.append(f)
    return out


@metadata_app.command("search")
def search(
    resource: Annotated[str, typer.Argument(..., help="Collection name, e.g. dataElements, users, organisationUnits")],
    base_url: Annotated[Optional[str], typer.Option(None, "--base-url")],
    username: Annotated[Optional[str], typer.Option(None, "--username")],
    password: Annotated[Optional[str], typer.Option(None, "--password", prompt=False, hide_input=True)],
    token: Annotated[Optional[str], typer.Option(None, "--token")],
    password_stdin: Annotated[bool, typer.Option(False, "--password-stdin")],
    engine: Annotated[Optional[str], typer.Option(None, "--engine", help="sync|async")],
    profile: Annotated[Optional[str], typer.Option(None, "--profile")],
    fields: Annotated[list[str], typer.Option([], "--fields", help="Projection fields")],
    filter_: Annotated[list[str], typer.Option([], "--filter", help="key:op:value (repeatable)")],
    order: Annotated[Optional[str], typer.Option(None, "--order", help="e.g. name:asc")],
    query: Annotated[Optional[str], typer.Option(None, "--query", help="Full-text query where supported")],
    page_size: Annotated[Optional[int], typer.Option(None, "--page-size")],
    all_pages: Annotated[bool, typer.Option(False, "--all", help="Iterate all pages")],
    output: Annotated[Optional[str], typer.Option("table", "--output")],
    jq: Annotated[Optional[str], typer.Option(None, "--jq")],
    array_key: Annotated[
        Optional[str], typer.Option(None, "--array-key", help="Collection key (defaults to resource)")
    ],
    verbose: Annotated[bool, typer.Option(False, "--verbose", help="Show full error details on failure.")],
):
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)
    array_key = array_key or resource

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
        array_key=array_key,
    )
    settings = make_settings(cfg)

    params: Dict[str, Any] = {"paging": True, "pageSize": cfg.page_size, "page": 1}
    if fields:
        params["fields"] = ",".join(fields)
    if order:
        params["order"] = order
    if query:
        params["query"] = query
    if filter_:
        params["filter"] = _parse_filters(filter_)

    path = f"/api/{resource}"

    try:
        if cfg.engine == "async":

            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    if cfg.all_pages:
                        first = await client.get(path, params=params)
                        items = _normalize_collection(first, cfg.array_key)
                        pager = int(first.get("pager", {}).get("pageCount", 1)) if isinstance(first, dict) else 1
                        for p in range(2, pager + 1):
                            res = await client.get(path, params={**params, "page": p})
                            items.extend(_normalize_collection(res, cfg.array_key))
                        return items
                    res = await client.get(path, params=params)
                    return _normalize_collection(res, cfg.array_key)

            data = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                if cfg.all_pages:
                    first = client.get(path, params=params)
                    items = _normalize_collection(first, cfg.array_key)
                    pager = int(first.get("pager", {}).get("pageCount", 1)) if isinstance(first, dict) else 1
                    for p in range(2, pager + 1):
                        res = client.get(path, params={**params, "page": p})
                        items.extend(_normalize_collection(res, cfg.array_key))
                    data = items
                else:
                    res = client.get(path, params=params)
                    data = _normalize_collection(res, cfg.array_key)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(data, output=cfg.output, fields=cfg.fields, jq=cfg.jq)


@metadata_app.command("show")
def show(
    resource: Annotated[str, typer.Argument(..., help="e.g. dataElements")],
    id: Annotated[str, typer.Argument(..., help="UID")],
    base_url: Annotated[Optional[str], typer.Option(None, "--base-url")],
    username: Annotated[Optional[str], typer.Option(None, "--username")],
    password: Annotated[Optional[str], typer.Option(None, "--password", prompt=False, hide_input=True)],
    token: Annotated[Optional[str], typer.Option(None, "--token")],
    password_stdin: Annotated[bool, typer.Option(False, "--password-stdin")],
    engine: Annotated[Optional[str], typer.Option(None, "--engine", help="sync|async")],
    profile: Annotated[Optional[str], typer.Option(None, "--profile")],
    fields: Annotated[list[str], typer.Option([], "--fields")],
    output: Annotated[Optional[str], typer.Option("json", "--output")],
    jq: Annotated[Optional[str], typer.Option(None, "--jq")],
    verbose: Annotated[bool, typer.Option(False, "--verbose")],
):
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg = resolve_settings(
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
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
    )
    settings = make_settings(cfg)

    path = f"/api/{resource}/{id}"
    params = {}
    if fields:
        params["fields"] = ",".join(fields)

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


@metadata_app.command("create")
def create(
    resource: Annotated[str, typer.Argument(..., help="e.g. dataElements")],
    json_body: Annotated[str, typer.Option(..., "--json", help="Raw JSON, @file.json")],
    base_url: Annotated[Optional[str], typer.Option(None, "--base-url")],
    username: Annotated[Optional[str], typer.Option(None, "--username")],
    password: Annotated[Optional[str], typer.Option(None, "--password", prompt=False, hide_input=True)],
    token: Annotated[Optional[str], typer.Option(None, "--token")],
    password_stdin: Annotated[bool, typer.Option(False, "--password-stdin")],
    engine: Annotated[Optional[str], typer.Option(None, "--engine", help="sync|async")],
    profile: Annotated[Optional[str], typer.Option(None, "--profile")],
    output: Annotated[Optional[str], typer.Option("json", "--output")],
    jq: Annotated[Optional[str], typer.Option(None, "--jq")],
    verbose: Annotated[bool, typer.Option(False, "--verbose")],
):
    from ..http import _load_json_arg

    payload = _load_json_arg(json_body)

    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg = resolve_settings(
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
    path = f"/api/{resource}"

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
        raise typer.Exit(code=4) from e

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)


@metadata_app.command("update")
def update(
    resource: Annotated[str, typer.Argument(..., help="e.g. dataElements")],
    id: Annotated[str, typer.Argument(..., help="UID")],
    json_body: Annotated[str, typer.Option(..., "--json", help="Raw JSON, @file.json")],
    base_url: Annotated[Optional[str], typer.Option(None, "--base-url")],
    username: Annotated[Optional[str], typer.Option(None, "--username")],
    password: Annotated[Optional[str], typer.Option(None, "--password", prompt=False, hide_input=True)],
    token: Annotated[Optional[str], typer.Option(None, "--token")],
    password_stdin: Annotated[bool, typer.Option(False, "--password-stdin")],
    engine: Annotated[Optional[str], typer.Option(None, "--engine", help="sync|async")],
    profile: Annotated[Optional[str], typer.Option(None, "--profile")],
    output: Annotated[Optional[str], typer.Option("json", "--output")],
    jq: Annotated[Optional[str], typer.Option(None, "--jq")],
    verbose: Annotated[bool, typer.Option(False, "--verbose")],
):
    from ..http import _load_json_arg

    payload = _load_json_arg(json_body)

    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg = resolve_settings(
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
    path = f"/api/{resource}/{id}"

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
        raise typer.Exit(code=4) from e

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)


@metadata_app.command("delete")
def delete(
    resource: Annotated[str, typer.Argument(..., help="e.g. dataElements")],
    id: Annotated[str, typer.Argument(..., help="UID")],
    base_url: Annotated[Optional[str], typer.Option(None, "--base-url")],
    username: Annotated[Optional[str], typer.Option(None, "--username")],
    password: Annotated[Optional[str], typer.Option(None, "--password", prompt=False, hide_input=True)],
    token: Annotated[Optional[str], typer.Option(None, "--token")],
    password_stdin: Annotated[bool, typer.Option(False, "--password-stdin")],
    engine: Annotated[Optional[str], typer.Option(None, "--engine", help="sync|async")],
    profile: Annotated[Optional[str], typer.Option(None, "--profile")],
    output: Annotated[Optional[str], typer.Option("json", "--output")],
    jq: Annotated[Optional[str], typer.Option(None, "--jq")],
    verbose: Annotated[bool, typer.Option(False, "--verbose")],
):
    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg = resolve_settings(
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
    path = f"/api/{resource}/{id}"

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
        raise typer.Exit(code=4) from e

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)


@metadata_app.command("bulk-import")
def bulk_import(
    source: Annotated[str, typer.Option(..., "--source", help="JSON text, @file.json, or '-' for stdin")],
    dry_run: Annotated[bool, typer.Option(False, "--dry-run/--commit")],
    param: Annotated[
        list[str],
        typer.Option(
            [], "--param", help="Extra query params key=value (e.g., importStrategy=CREATE_AND_UPDATE, atomicMode=ALL)"
        ),
    ],
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
    """POST /api/metadata with a DHIS2 metadata JSON document."""
    import gzip
    import json
    from pathlib import Path

    def _read_json_from(src: str):
        if src == "-":
            return json.loads(sys.stdin.read())
        if src.startswith("@"):
            p = Path(src[1:])
            data = p.read_bytes()
            if p.suffix == ".gz":
                data = gzip.decompress(data)
            return json.loads(data.decode("utf-8"))
        return json.loads(src)

    def _parse_params(items: list[str]) -> dict[str, str]:
        params: dict[str, str] = {}
        for it in items:
            if "=" not in it:
                raise typer.BadParameter(f"Invalid --param '{it}', expected key=value")
            k, v = it.split("=", 1)
            params[k] = v
        return params

    payload = _read_json_from(source)

    pw = password
    if password_stdin and not token:
        pw = sys.stdin.readline().rstrip("\n")
    if username and not pw and not token:
        pw = typer.prompt("Password", hide_input=True)

    cfg = resolve_settings(
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

    params = _parse_params(param)
    if dry_run:
        params["dryRun"] = "true"
    path = "/api/metadata"
    if params:
        from urllib.parse import urlencode

        path = f"{path}?{urlencode(params, doseq=True)}"

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
        raise typer.Exit(code=4) from e

    render_output(res, output=cfg.output, fields=[], jq=cfg.jq)
