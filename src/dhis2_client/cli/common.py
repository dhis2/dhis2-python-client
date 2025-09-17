from __future__ import annotations

import asyncio
import sys
import traceback
from dataclasses import dataclass
from typing import Optional, Sequence, Any, Dict

from pydantic import SecretStr

from dhis2_client.exceptions import DHIS2Error, NetworkError
from dhis2_client.settings import Settings


@dataclass
class CLISettings:
    base_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    timeout: Optional[float] = None
    verify_ssl: Optional[bool] = None
    log_level: Optional[str] = None
    engine: Optional[str] = None
    output: Optional[str] = None
    fields: Sequence[str] = ()
    jq: Optional[str] = None
    profile: Optional[str] = None
    page_size: Optional[int] = None
    all_pages: bool = False
    password_stdin: bool = False
    array_key: Optional[str] = None
    # Tri-state override for return style:
    #   None  -> follow Settings.return_models (env/config default)
    #   True  -> return dict/JSON
    #   False -> return Pydantic models
    as_dict: Optional[bool] = None


def resolve_settings(
    *,
    base_url: Optional[str],
    username: Optional[str],
    password: Optional[str],
    token: Optional[str],
    timeout: Optional[float],
    verify_ssl: Optional[bool],
    log_level: Optional[str],
    engine: Optional[str],
    output: Optional[str],
    fields: Sequence[str],
    jq: Optional[str],
    profile: Optional[str],
    page_size: Optional[int],
    all_pages: bool,
    password_stdin: bool,
    array_key: Optional[str],
    as_dict: Optional[bool] = None,
) -> CLISettings:
    """Collect parsed CLI options into a single dataclass (no side-effects)."""
    return CLISettings(
        base_url=base_url,
        username=username,
        password=password,
        token=token,
        timeout=timeout,
        verify_ssl=verify_ssl,
        log_level=log_level,
        engine=engine,
        output=output,
        fields=fields,
        jq=jq,
        profile=profile,
        page_size=page_size,
        all_pages=all_pages,
        password_stdin=password_stdin,
        array_key=array_key,
        as_dict=as_dict,
    )


def make_settings(cfg: CLISettings) -> Settings:
    """
    Build the Pydantic Settings model from CLISettings.

    If cfg.as_dict is None -> do not override Settings.return_models (use defaults/env).
    If cfg.as_dict is True  -> return_models=False (dict/JSON).
    If cfg.as_dict is False -> return_models=True  (Pydantic models).
    """
    kwargs: Dict[str, Any] = dict(
        base_url=cfg.base_url,
        verify_ssl=True if cfg.verify_ssl is None else cfg.verify_ssl,
        timeout=30.0 if cfg.timeout is None else float(cfg.timeout),
        username=cfg.username,
        password=SecretStr(cfg.password) if cfg.password else None,
        token=SecretStr(cfg.token) if cfg.token else None,
        log_level=cfg.log_level or "WARNING",
    )
    if cfg.as_dict is not None:
        kwargs["return_models"] = not cfg.as_dict
    return Settings(**kwargs)


def _format_conflict(c: dict) -> str:
    """Format a DHIS2 import conflict safely like 'object: message'."""
    obj = c.get("object", "?")
    msg = c.get("value") or c.get("message") or "?"
    return f"{obj}: {msg}"


def print_http_error(e: BaseException, *, verbose: bool = False) -> None:
    """
    Compact error output for DHIS2Error/NetworkError and generic exceptions.

    - Prints status code, path, and message when available.
    - If DHIS2 import report details contain conflicts, shows a concise summary.
    """
    parts = []
    if isinstance(e, (DHIS2Error, NetworkError)):
        status = getattr(e, "status_code", None)
        path = getattr(e, "path", None)
        msg = getattr(e, "message", None) or str(e)
        if status is not None:
            parts.append(f"status={status}")
        if path:
            parts.append(f"path={path}")
        parts.append(msg)

        # Optional details payload from server (import reports, etc.)
        details = getattr(e, "details", None)
        if isinstance(details, dict):
            response = details.get("response") or {}
            conflicts = response.get("conflicts") or response.get("errorReports") or []
            if isinstance(conflicts, list) and conflicts:
                brief = "; ".join(_format_conflict(c) for c in conflicts[:5])
                if len(conflicts) > 5:
                    brief += f" (+{len(conflicts)-5} more)"
                parts.append(f"conflicts={brief}")
    else:
        parts.append(str(e) or e.__class__.__name__)

    print(f"ERROR: {' | '.join(parts)}", file=sys.stderr)
    if verbose:
        traceback.print_exc(file=sys.stderr)


def run_async(coro):
    """
    Run an async coroutine from sync code.
    - In a normal CLI (no running loop), uses asyncio.run(coro).
    - If a loop is already running (e.g., embedded/REPL), spins a temp loop.
    """
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
