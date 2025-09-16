from __future__ import annotations

import typer

from .http import http_app
from .periods import periods_app
from .resources.bulk import bulk_app
from .resources.data_value_sets import dvs_app
from .resources.data_values import data_values_app
from .resources.metadata import metadata_app
from .resources.users import users_app
from .system import system_app

app = typer.Typer(
    add_completion=True,
    help="DHIS2 Web API CLI (sync by default; use --engine async to opt in)."
)

app.add_typer(system_app, name="system")
app.add_typer(http_app,   name="http")
app.add_typer(periods_app, name="period")
app.add_typer(users_app,    name="users")
app.add_typer(metadata_app,   name="metadata")
app.add_typer(data_values_app, name="data-values")
app.add_typer(dvs_app,         name="data-value-sets")
app.add_typer(bulk_app, name="bulk")
