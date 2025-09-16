from __future__ import annotations

import sys
from typing import Optional

import typer

from dhis2_client import DHIS2AsyncClient, DHIS2Client

from .common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from .output import render_output

system_app = typer.Typer(help="System helpers")


@system_app.command("info")
def system_info(
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    username: Optional[str] = typer.Option(None, "--username"),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        prompt=False,
        hide_input=True,
        help="Prefer prompt/STDIN over passing on the CLI.",
    ),
    token: Optional[str] = typer.Option(
        None,
        "--token",
        help="Preferred over username/password.",
    ),
    password_stdin: bool = typer.Option(
        False,
        "--password-stdin",
        help="Read password from STDIN (safer for scripts).",
    ),
    timeout: Optional[float] = typer.Option(None, "--timeout"),
    verify_ssl: Optional[bool] = typer.Option(None, "--verify-ssl/--insecure"),
    log_level: Optional[str] = typer.Option(None, "--log-level"),
    engine: Optional[str] = typer.Option(
        None,
        "--engine",
        help="sync|async (default: sync)",
    ),
    output: Optional[str] = typer.Option("table", "--output"),
    field: list[str] = typer.Option([], "--fields"),
    jq: Optional[str] = typer.Option(None, "--jq"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    verbose: bool = typer.Option(False, "--verbose", help="Show full error details on failure."),
) -> None:
    # SECURITY: read password safely if needed
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
                    return await client.get_system_info()
            data = run_async(_run())
        else:
            with DHIS2Client.from_settings(settings) as client:
                data = client.get_system_info()
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4)

    render_output(data, output=cfg.output, fields=cfg.fields, jq=cfg.jq)
