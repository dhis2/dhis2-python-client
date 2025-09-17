from __future__ import annotations

import sys
from typing import Annotated, Optional, TYPE_CHECKING

import typer
from click import Choice  # <-- use Click's Choice for robust value validation

from .common import CLISettings, make_settings, print_http_error, resolve_settings, run_async
from .output import render_output
from .utils import parse_bool_opt, to_plain_json

if TYPE_CHECKING:
    from dhis2_client import DHIS2Client, DHIS2AsyncClient

system_app = typer.Typer(help="System helpers")
Option = typer.Option


@system_app.command("info")
def system_info(
    # config & auth
    base_url: Annotated[Optional[str], Option("--base-url", help="DHIS2 base URL (e.g., http://localhost:8080)")] = None,
    username: Annotated[Optional[str], Option("--username")] = None,
    password: Annotated[
        Optional[str],
        Option("--password", prompt=False, hide_input=True, help="Prefer prompt/STDIN over passing on the CLI.")
    ] = None,
    token: Annotated[Optional[str], Option("--token", help="Preferred over username/password.")] = None,
    password_stdin: Annotated[bool, Option("--password-stdin", is_flag=True, help="Read password from STDIN (safer for scripts).")] = False,

    # runtime options
    timeout: Annotated[Optional[float], Option("--timeout")] = None,
    verify_ssl: Annotated[Optional[bool], Option("--verify-ssl/--insecure")] = None,

    # validated log level via Click Choice (keeps Annotated type as str)
    log_level: Annotated[
        Optional[str],
        Option(
            "--log-level",
            click_type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
            help="DEBUG|INFO|WARNING|ERROR|CRITICAL",
        ),
    ] = None,

    # engine/output validated by Click Choice (no Literal/Enum types)
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

    # formatting / filters
    field: Annotated[list[str], Option("--fields", help="Repeatable: --fields id --fields name")] = [],
    jq: Annotated[Optional[str], Option("--jq", help="jq-style filter (applied after fetch)")] = None,

    # profile & verbosity
    profile: Annotated[Optional[str], Option("--profile", help="Named profile from config (if supported)")] = None,
    verbose: Annotated[bool, Option("--verbose", is_flag=True, help="Show full error details on failure.")] = False,

    # return-style override (parsed later to bool)
    as_dict: Annotated[Optional[str], Option("--as-dict", metavar="BOOL", help="true/false. Omit to use Settings.return_models default.")] = None,
) -> None:
    # SECURITY: resolve password safely
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
        log_level=(log_level.upper() if log_level else None),  # normalize to upper for Settings
        engine=engine.lower(),   # "sync" | "async"
        output=output.lower(),   # "table" | "json" | "yaml"
        fields=field,
        jq=jq,
        profile=profile,
        page_size=None,
        all_pages=False,
        password_stdin=password_stdin,
        array_key=None,
        as_dict=parse_bool_opt(as_dict),  # None -> use Settings.return_models
    )
    settings = make_settings(cfg)

    try:
        if cfg.engine == "async":
            from dhis2_client import DHIS2AsyncClient
            async def _run():
                async with DHIS2AsyncClient.from_settings(settings) as client:
                    return await client.get_system_info(as_dict=cfg.as_dict)
            data = run_async(_run())
        else:
            from dhis2_client import DHIS2Client
            with DHIS2Client.from_settings(settings) as client:
                data = client.get_system_info(as_dict=cfg.as_dict)
    except Exception as e:
        print_http_error(e, verbose=verbose)
        raise typer.Exit(code=4) from e

    render_output(to_plain_json(data), output=cfg.output, fields=cfg.fields, jq=cfg.jq)
