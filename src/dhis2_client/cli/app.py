from __future__ import annotations

from typing import Any, Dict, List, Optional

import typer
from rich.console import Console

from .output import print_output
from .utils import build_settings_with_overrides, iter_pages, run

try:
    from dhis2_client.async_client import DHIS2AsyncClient  # noqa: F401
    from dhis2_client.sync_client import DHIS2Client  # noqa: F401
except Exception:  # pragma: no cover
    DHIS2AsyncClient = None  # type: ignore
    DHIS2Client = None  # type: ignore

console = Console()
app = typer.Typer(help="DHIS2 client CLI")

# ------------------------- connection options -------------------------

@app.callback()
def main(
    ctx: typer.Context,
    base_url: Optional[str] = typer.Option(None, "--base-url", envvar="DHIS2_BASE_URL", help="DHIS2 base URL"),
    username: Optional[str] = typer.Option(None, "--username", envvar="DHIS2_USERNAME", help="Basic auth username"),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        envvar="DHIS2_PASSWORD",
        help="Basic auth password",
        prompt=False,
        hide_input=True),
    token: Optional[str] = typer.Option(None, "--token", envvar="DHIS2_TOKEN", help="API token (PAT)"),
):
    """
    Set connection/auth parameters for this invocation.
    """
    try:
        settings = build_settings_with_overrides(base_url=base_url, username=username, password=password, token=token)
        ctx.obj = {"settings": settings}
    except Exception as e:  # pragma: no cover
        console.print(f"[red]Error[/red] {e}")
        raise typer.Exit(code=2) from e

# ------------------------- GET (raw) -------------------------

@app.command("get")
def cmd_get(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="API path, e.g. /api/organisationUnits"),
    fields: Optional[List[str]] = typer.Option(None, "--fields", help="Repeatable: field list to include"),
    page_size: int = typer.Option(100, "--page-size", min=1, max=200000),
    all: bool = typer.Option(False, "--all", help="Iterate all pages and stream/aggregate results"),
    sync: bool = typer.Option(False, "--sync", help="Use synchronous client (default async)"),
):
    """
    Raw GET request. Use --all for automatic paging.
    """
    settings = ctx.obj["settings"]

    # Add fields/pageSize/paging only when hitting collection endpoints (best effort).
    def _mk_params(paging_flag: bool) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)
        if all or paging_flag:
            params["pageSize"] = page_size
            params["paging"] = "true"
        return params

    # SYNC mode
    if sync:
        if DHIS2Client is None:  # pragma: no cover
            console.print("[red]Synchronous client unavailable[/red]")
            raise typer.Exit(code=2)
        with DHIS2Client.from_settings(settings) as client:
            if all:
                # manual paging in sync mode
                current = 1
                while True:
                    p = _mk_params(True)
                    p["page"] = current
                    res = client.get_sync(path, params=p)
                    print_output(res)
                    pager = res.get("pager") or {}
                    page = pager.get("page")
                    page_count = pager.get("pageCount")
                    next_page_url = pager.get("nextPage") or res.get("nextPage")
                    if page_count and page:
                        if page >= page_count:
                            break
                        current += 1
                    elif next_page_url:
                        current += 1
                    else:
                        break
                return
            # single page
            res = client.get_sync(path, params=_mk_params(False))
            print_output(res)
            return

    # ASYNC mode
    if DHIS2AsyncClient is None:  # pragma: no cover
        console.print("[red]Async client unavailable[/red]")
        raise typer.Exit(code=2)

    async def _run():
        async with DHIS2AsyncClient.from_settings(settings) as client:
            if all:
                async for page in iter_pages(client, path, params=_mk_params(True), page_size=page_size):
                    print_output(page)
                return
            res = await client.get_async(path, params=_mk_params(False))
            print_output(res)

    try:
        run(_run())
    except Exception as e:  # pragma: no cover
        console.print(f"[red]Error[/red] {e}")
        raise typer.Exit(code=2) from e

# ------------------------- Period helpers -------------------------

@app.command("validate-period")
def cmd_validate_period(
    type: str = typer.Argument(..., help="DHIS2 period type"),
    value: str = typer.Argument(..., help="Period value"),
):
    """Validate a period value for a given type."""
    try:
        from dhis2_client.periods import validate_period  # type: ignore
        ok = validate_period(type, value)
        if bool(ok):
            console.print("valid")
            raise typer.Exit(code=0)
        console.print("invalid")
        raise typer.Exit(code=1)
    except ValueError as e:
        console.print(f"invalid: {e}")
        raise typer.Exit(code=1) from e
    except Exception:
        if value and isinstance(value, str):
            console.print("valid (basic)")
            raise typer.Exit(code=0) from None
        console.print("invalid")
        raise typer.Exit(code=1) from None

@app.command("period-from-date")
def cmd_period_from_date(
    type: str = typer.Argument(..., help="DHIS2 period type"),
    date: str = typer.Argument(..., help="Date in ISO format (yyyy-mm-dd)"),
):
    """Format a date into a period of the given type."""
    try:
        from dhis2_client.periods import period_from_date  # type: ignore
        console.print(period_from_date(type, date))
    except Exception:
        console.print(date)
