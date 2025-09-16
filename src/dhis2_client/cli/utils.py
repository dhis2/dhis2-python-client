from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, Optional

try:
    # Pydantic v2
    from pydantic import BaseModel as PydanticBaseModel  # type: ignore
except Exception:  # pragma: no cover
    PydanticBaseModel = object  # fallback, just in case


def run(coro):
    return asyncio.run(coro)


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
