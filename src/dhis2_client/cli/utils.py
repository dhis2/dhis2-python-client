from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, Optional


def run(coro):
    return asyncio.run(coro)


async def iter_pages(client, path: str, params: Optional[Dict[str, Any]] = None, page_size: int = 100) -> AsyncIterator[dict]:
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


def build_settings_with_overrides(*, base_url: Optional[str], username: Optional[str], password: Optional[str], token: Optional[str]):
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