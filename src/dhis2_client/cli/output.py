from __future__ import annotations

import json
from typing import Any, Iterable, Mapping, Sequence

import yaml
from rich.console import Console
from rich.table import Table

from .utils import make_json_safe, to_plain

console = Console()

def _is_mapping(x: Any) -> bool:
    return isinstance(x, Mapping)

def _is_sequence_of_mappings(x: Any) -> bool:
    return isinstance(x, Sequence) and x and all(isinstance(i, Mapping) for i in x)

def _stringify(x: Any) -> str:
    if isinstance(x, (dict, list, tuple, set)):
        try:
            return json.dumps(x, ensure_ascii=False)
        except Exception:
            return str(x)
    return str(x)

def _render_kv_table(d: Mapping[str, Any]) -> None:
    table = Table(show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for k, v in d.items():
        table.add_row(str(k), _stringify(v))
    console.print(table)

def _render_list_table(rows: Iterable[Mapping[str, Any]]) -> None:
    rows = list(rows)
    first_keys = list(rows[0].keys()) if rows else []
    extra_keys, seen = [], set(first_keys)
    for r in rows[1:]:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                extra_keys.append(k)
    cols = first_keys + extra_keys

    table = Table()
    for c in cols:
        table.add_column(str(c))
    for r in rows:
        table.add_row(*[_stringify(r.get(c, "")) for c in cols])
    console.print(table)

def print_output(result: Any, output: str = "json") -> None:
    """
    Print result in the requested format.
    Accepts Pydantic models, dicts, lists – converts via to_plain().
    Then coerces non-JSON types (e.g., Url) via make_json_safe().
    """
    data = to_plain(result)
    safe = make_json_safe(data)

    if output == "json":
        # rich.print_json needs either serializable data=... OR a JSON string.
        console.print_json(json=json.dumps(safe, ensure_ascii=False))
        return

    if output == "yaml":
        console.print(yaml.safe_dump(safe, sort_keys=False).rstrip())
        return

    if output == "ndjson":
        if isinstance(safe, Sequence) and not isinstance(safe, (str, bytes)):
            for item in safe:
                console.print(json.dumps(make_json_safe(item), ensure_ascii=False))
        else:
            console.print(json.dumps(safe, ensure_ascii=False))
        return

    if output == "table":
        if isinstance(safe, Mapping):
            _render_kv_table(safe)
            return
        if isinstance(safe, Sequence) and safe and all(isinstance(i, Mapping) for i in safe):
            _render_list_table(safe)
            return
        console.print_json(json=json.dumps(safe, ensure_ascii=False))
        return

    console.print_json(json=json.dumps(safe, ensure_ascii=False))
