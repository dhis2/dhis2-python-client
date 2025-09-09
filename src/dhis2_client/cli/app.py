from __future__ import annotations

from typing import List, Optional

import typer
from rich.console import Console

from .output import print_output
from .utils import run, iter_pages, build_settings_with_overrides

# ---- Import your library -------------------------------------------------
# TODO(repo): adjust imports if your package structure differs
try:
    from dhis2_client.async_client import DHIS2AsyncClient  # preferred path
except Exception:  # pragma: no cover
    from dhis2_client import DHIS2AsyncClient  # fallback
# -------------------------------------------------------------------------

app = typer.Typer(help="DHIS2 Web API CLI")
console = Console()


# Global options (auth/connection). Values default from env via Settings(),
# but these flags let users run one-off commands without exporting env vars.
@app.callback()
def main(
    ctx: typer.Context,
    base_url: Optional[str] = typer.Option(None, "--base-url", envvar="DHIS2_BASE_URL", help="DHIS2 base URL, e.g. https://play.dhis2.org/dev"),
    username: Optional[str] = typer.Option(None, "--username", envvar="DHIS2_USERNAME", help="Username for basic auth"),
    password: Optional[str] = typer.Option(None, "--password", envvar="DHIS2_PASSWORD", help="Password for basic auth", prompt=False, hide_input=True),
    token: Optional[str] = typer.Option(None, "--token", envvar="DHIS2_TOKEN", help="API token / PAT (overrides basic auth if provided)"),
):
    """Set connection/auth parameters for this invocation.

    SECURITY: Avoid passing --password on shared systems; prefer the prompt or env vars.
    """
    ctx.obj = {
        "base_url": base_url,
        "username": username,
        "password": password,
        "token": token,
    }


@app.command()
def system_info(
    ctx: typer.Context,
    output: str = typer.Option("json", "--output", help="json|yaml|table|ndjson"),
) -> None:
    """Fetch /api/system/info."""

    overrides = ctx.obj or {}
    settings = build_settings_with_overrides(
        base_url=overrides.get("base_url"),
        username=overrides.get("username"),
        password=overrides.get("password"),
        token=overrides.get("token"),
    )

    async def _main():
        async with DHIS2AsyncClient.from_settings(settings) as client:  # type: ignore[attr-defined]
            try:
                return await client.get_system_info()  # type: ignore[attr-defined]
            except Exception:
                return await client.get("/api/system/info")

    try:
        data = run(_main())
        print_output(data, output)
    except Exception as e:
        console.print(f"[red]Error[/red] {e}")
        raise typer.Exit(code=2)


@app.command()
def get(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="API path, e.g. /api/organisationUnits"),
    fields: Optional[List[str]] = typer.Option(None, "--fields", help="Repeatable: field list to include"),
    page_size: int = typer.Option(100, "--page-size", min=1, max=200000),
    all: bool = typer.Option(False, "--all", help="Iterate all pages and stream/aggregate results"),
    output: str = typer.Option("json", "--output", help="json|yaml|table|ndjson"),
) -> None:
    """Generic GET with optional paging and field selection."""

    overrides = ctx.obj or {}
    settings = build_settings_with_overrides(
        base_url=overrides.get("base_url"),
        username=overrides.get("username"),
        password=overrides.get("password"),
        token=overrides.get("token"),
    )

    async def _main():
        async with DHIS2AsyncClient.from_settings(settings) as client:  # type: ignore[attr-defined]
            params = {}
            if fields:
                params["fields"] = ",".join(fields)
            if all:
                collected = []
                async for page in iter_pages(client, path, params=params, page_size=page_size):
                    if isinstance(page, dict):
                        for v in page.values():
                            if isinstance(v, list):
                                collected.extend(v)
                                break
                        else:
                            collected.append(page)
                    else:
                        collected.append(page)
                return collected
            else:
                return await client.get(path, params=params)

    try:
        data = run(_main())
        print_output(data, output)
    except Exception as e:
        console.print(f"[red]Error[/red] {e}")
        raise typer.Exit(code=2)


# ---- Period utilities ----------------------------------------------------
period = typer.Typer(help="Period helpers")
app.add_typer(period, name="period")


@period.command("validate")
def period_validate(
    ctx: typer.Context,
    type: str = typer.Argument(..., help="e.g. Monthly, Weekly, Daily"),
    value: str = typer.Argument(...),
) -> None:
    """Validate a DHIS2 period string (best-effort)."""

    # Settings not currently needed here, but keeping structure consistent
    overrides = ctx.obj or {}
    _ = build_settings_with_overrides(
        base_url=overrides.get("base_url"),
        username=overrides.get("username"),
        password=overrides.get("password"),
        token=overrides.get("token"),
    )

    try:
        from dhis2_client.periods import validate_period  # type: ignore
        ok = validate_period(type, value)
        if ok is True or ok == (True):
            console.print("valid")
            raise typer.Exit(code=0)
        console.print("invalid")
        raise typer.Exit(code=1)
    except Exception:
        if value and isinstance(value, str):
            console.print("valid (basic)")
            raise typer.Exit(code=0)
        console.print("invalid")
        raise typer.Exit(code=1)


@period.command("format")
def period_format(
    ctx: typer.Context,
    type: str = typer.Argument(..., help="e.g. Weekly"),
    date: str = typer.Argument(..., help="YYYY-MM-DD"),
) -> None:
    """Format a date into a DHIS2 period string (best-effort)."""

    overrides = ctx.obj or {}
    _ = build_settings_with_overrides(
        base_url=overrides.get("base_url"),
        username=overrides.get("username"),
        password=overrides.get("password"),
        token=overrides.get("token"),
    )

    try:
        from dhis2_client.periods import period_from_date  # type: ignore
        console.print(period_from_date(type, date))
    except Exception:
        console.print(date)