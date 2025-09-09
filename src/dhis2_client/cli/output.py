from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from rich.console import Console
from rich.table import Table

console = Console()


def print_output(data: Any, output: str = "json") -> None:
    """Pretty-print data in the requested format.

    Supported: json (default), yaml, table, ndjson
    """
    output = (output or "json").lower()
    if output == "json":
        console.print_json(data=data)
        return

    if output == "yaml":
        try:
            import yaml  # type: ignore
        except Exception as e:  # pragma: no cover
            console.print(f"[red]pyyaml not installed:[/red] {e}")
            console.print_json(data=data)
            return
        console.print(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
        return

    if output == "ndjson":
        if isinstance(data, Iterable) and not isinstance(data, (str, bytes, Mapping)):
            for item in data:
                console.print(json.dumps(item, ensure_ascii=False))
        else:
            console.print(json.dumps(data, ensure_ascii=False))
        return

    if output == "table":
        # Accept list[dict] best-effort
        if isinstance(data, Iterable) and not isinstance(data, (str, bytes, Mapping)):
            rows = list(data)
            if not rows:
                console.print("(empty)")
                return
            first = rows[0]
            if isinstance(first, Mapping):
                cols = list(first.keys())
                table = Table(show_header=True, header_style="bold")
                for c in cols:
                    table.add_column(str(c))
                for row in rows:
                    if isinstance(row, Mapping):
                        table.add_row(*(str(row.get(c, "")) for c in cols))
                    else:
                        table.add_row(str(row))
                console.print(table)
                return
        # Fallback
        console.print_json(data=data)
        return

    # Unknown -> default json
    console.print_json(data=data)