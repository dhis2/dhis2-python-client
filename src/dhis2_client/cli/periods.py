from __future__ import annotations
import typer
from datetime import date

# Wire to your real helpers once ready:
# from dhis2_client.models import validate_period, format_period

periods_app = typer.Typer(help="Period utilities")

@periods_app.command("validate")
def validate_cmd(period_type: str, period: str):
    # validate_period(period_type, period)  # raise if invalid
    typer.secho("OK", fg=typer.colors.GREEN)

@periods_app.command("format")
def format_cmd(period_type: str, year: int, month: int = 1, day: int = 1):
    # p = format_period(period_type, date(year, month, day))
    # typer.echo(p)
    typer.echo(f"{period_type}:{year:04d}-{month:02d}-{day:02d}")
