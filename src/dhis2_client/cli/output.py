from __future__ import annotations

import dataclasses
import json
import sys
from enum import Enum
from typing import Any

import jmespath
import yaml
from rich.console import Console
from rich.table import Table

_console = Console()


def _to_plain(obj: Any) -> Any:
    # Scalars
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Collections
    if isinstance(obj, (list, tuple, set)):
        return [_to_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}

    # Dataclasses
    if dataclasses.is_dataclass(obj):
        return _to_plain(dataclasses.asdict(obj))

    # Enums
    if isinstance(obj, Enum):
        return _to_plain(obj.value)

    # Pydantic v2
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return _to_plain(obj.model_dump())
        except Exception:
            pass

    # Pydantic v1
    if hasattr(obj, "dict") and callable(obj.dict):
        try:
            return _to_plain(obj.dict())
        except Exception:
            pass

    # URL-like or anything else: stringify
    try:
        return str(obj)
    except Exception:
        return repr(obj)


def render_output(data: Any, *, output: str, fields: list[str] | None = None, jq: str | None = None):
    # Normalize to plain Python types first
    data = _to_plain(data)

    # Optional JMESPath filter
    if jq:
        try:
            data = jmespath.search(jq, data)
        except Exception as e:
            _console.print(f"[red]JMESPath error:[/red] {e}\n[red]Query:[/red] {jq}")

    # JSON
    if output == "json":
        _console.print_json(data=data)
        return

    # YAML
    if output == "yaml":
        _console.print(yaml.safe_dump(data, sort_keys=False))
        return

    # NDJSON
    if output == "ndjson":
        if isinstance(data, list):
            for row in data:
                sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(json.dumps(data, ensure_ascii=False) + "\n")
        return

    # TABLE (default)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        cols = fields or list({k for row in data for k in row.keys()})
        table = Table()
        for c in cols:
            table.add_column(c)
        for row in data:
            table.add_row(*[str(row.get(c, "")) for c in cols])
        _console.print(table)
    else:
        # fallback to pretty JSON
        _console.print_json(data=data)
