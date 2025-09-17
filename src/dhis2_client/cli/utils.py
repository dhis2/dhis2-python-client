from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

import typer
from pydantic import BaseModel

try:
    # Pydantic v2
    from pydantic import BaseModel as PydanticBaseModel  # type: ignore
except Exception:  # pragma: no cover
    PydanticBaseModel = object  # fallback, just in case


__all__ = ["parse_params", "load_json_arg", "detect_array_key", "to_plain_json", "parse_bool_opt"]


_TRUE = {"1", "true", "t", "yes", "y", "on"}
_FALSE = {"0", "false", "f", "no", "n", "off"}

def run(coro):
    return asyncio.run(coro)

def parse_params(items: list[str]) -> dict:
    params: Dict[str, str] = {}
    for p in items:
        if "=" not in p:
            raise typer.BadParameter(f"Invalid --param '{p}', expected key=value")
        k, v = p.split("=", 1)
        params[k] = v
    return params


def load_json_arg(json_arg: Optional[str]) -> object | None:
    if not json_arg:
        return None
    if json_arg.startswith("@"):
        p = Path(json_arg[1:])
        return json.loads(p.read_text(encoding="utf-8"))
    return json.loads(json_arg)


def detect_array_key(obj: Dict[str, Any]) -> Optional[str]:
    # Heuristic: first list-of-dicts key
    for k, v in obj.items():
        if isinstance(v, list) and (not v or isinstance(v[0], dict)):
            return k
    return None


def to_plain_json(value: Any) -> Any:
    """Convert pydantic models/containers into plain JSON-compatible types."""
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return {k: to_plain_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_plain_json(v) for v in value]
    return value

def parse_bool_opt(value: Optional[str]) -> Optional[bool]:
    """
    Parse an optional string into a boolean.
    None     -> None (defer to Settings)
    'true'   -> True
    'false'  -> False
    Accepts common variants: 1/0, yes/no, on/off, t/f (case-insensitive).
    """
    if value is None:
        return None
    v = value.strip().lower()
    if v in _TRUE:
        return True
    if v in _FALSE:
        return False
    raise typer.BadParameter("as-dict must be a boolean: true/false")


async def iter_pages(
    client,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    page_size: int = 100,
) -> AsyncIterator[dict]:
    """Generic pager: expects DHIS2's standard paging params.

    If your client exposes specific iterators, feel free to swap this
    out with those for efficiency.
    """
    params = dict(params or {})
    page = 1
    while True:
        _params = {**params, "paging": True, "page": page, "pageSize": page_size}
        chunk = await client.get(path, params=_params)
        yield chunk
        pager = (chunk or {}).get("pager") or {}
        if not pager:
            break
        if pager.get("page", page) * pager.get("pageSize", page_size) >= pager.get("total", 0):
            break
        page += 1


def make_json_safe(obj: Any) -> Any:
    """
    Coerce non-JSON-serializable values (e.g., pydantic Url) to strings.
    Apply after to_plain().
    """
    # primitives
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    # containers
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        t = type(obj)
        return t(make_json_safe(v) for v in obj)
    # everything else -> string
    return str(obj)


def to_plain(obj: Any) -> Any:
    """
    Convert Pydantic models (and containers of models) into plain Python types.
    Works recursively, safe for dict/list/tuple/set.
    """
    if isinstance(obj, PydanticBaseModel):
        # Pydantic v2
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        # Pydantic v1 fallback
        if hasattr(obj, "dict"):
            return obj.dict()
    if isinstance(obj, dict):
        return {k: to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        t = type(obj)
        return t(to_plain(v) for v in obj)
    return obj


def build_settings_with_overrides(
    *,
    base_url: Optional[str],
    username: Optional[str],
    password: Optional[str],
    token: Optional[str],
):
    """Create Settings(), then override fields if CLI flags provided.

    This keeps compatibility with existing Settings() behavior (env/.env loading)
    while allowing users to pass one-off credentials on the CLI.
    """
    from dhis2_client import Settings  # local import to avoid circulars

    settings = Settings()
    if base_url:
        try:
            settings.base_url = base_url  # type: ignore[attr-defined]
        except Exception:
            pass
    if username is not None:
        try:
            settings.username = username  # type: ignore[attr-defined]
        except Exception:
            pass
    if password is not None:
        try:
            settings.password = password  # type: ignore[attr-defined]
        except Exception:
            pass
    if token is not None:
        try:
            settings.token = token  # type: ignore[attr-defined]
        except Exception:
            pass
    return settings
