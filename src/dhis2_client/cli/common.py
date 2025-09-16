from __future__ import annotations

import dataclasses
import os
import pathlib
from typing import Any, Dict, Optional

# tomllib for 3.11+, tomli fallback for 3.10
try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

from rich.console import Console

# Adjust these imports if your module names differ
from dhis2_client import Settings

DEFAULT_ENGINE = "sync"  # default mode if --engine omitted
_console = Console()


@dataclasses.dataclass
class CLISettings:
    base_url: str
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: float = 30.0
    verify_ssl: bool = True
    log_level: str = "WARNING"
    engine: str = DEFAULT_ENGINE                 # "sync" | "async"
    output: str = "table"                        # "table" | "json" | "yaml" | "ndjson"
    fields: list[str] = dataclasses.field(default_factory=list)
    jq: Optional[str] = None
    page_size: int = 100
    all_pages: bool = False
    # security
    password_stdin: bool = False
    # array key override for collections (e.g., dataElements, users)
    array_key: Optional[str] = None


def _load_config(profile: Optional[str]) -> Dict[str, Any]:
    for p in [
        pathlib.Path("/etc/dhis2-client/config.toml"),
        pathlib.Path.home() / ".config" / "dhis2-client" / "config.toml",
        pathlib.Path("config/dhis2-client.toml"),
    ]:
        if p.exists():
            with p.open("rb") as f:
                data = tomllib.load(f)
            return data.get(profile or "default", {})
    return {}


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
    fields: list[str],
    jq: Optional[str],
    profile: Optional[str],
    page_size: Optional[int],
    all_pages: bool,
    password_stdin: bool,
    array_key: Optional[str],
) -> CLISettings:
    cfg = {k.replace("-", "_"): v for k, v in _load_config(profile).items()}
    env = os.environ

    def pick(key: str, default=None):
        if key in cfg and cfg[key] is not None:
            return cfg[key]
        if env.get(key.upper()) is not None:
            return env.get(key.upper())
        return default

    base = base_url or pick("base_url")
    if not base:
        raise ValueError("Missing base URL. Use --base-url, a config profile, or DHIS2_BASE_URL.")

    return CLISettings(
        base_url=base,
        token=token or pick("token"),
        username=username or pick("username"),
        password=password or None,  # avoid loading passwords from env/config by default
        timeout=float(timeout or pick("timeout", 30)),
        verify_ssl=bool(verify_ssl if verify_ssl is not None else str(pick("verify_ssl", "true")).lower() != "false"),
        log_level=(log_level or pick("log_level", "WARNING")).upper(),
        engine=(engine or pick("engine", DEFAULT_ENGINE)).lower(),
        output=(output or pick("output", "table")).lower(),
        fields=fields or [],
        jq=jq or pick("jq"),
        page_size=int(page_size or pick("page_size", 100)),
        all_pages=all_pages or bool(pick("all_pages", False)),
        password_stdin=password_stdin,
        array_key=array_key or None,
    )


def make_settings(cfg: CLISettings) -> Settings:
    return Settings(
        base_url=cfg.base_url,
        username=cfg.username,
        password=cfg.password,
        token=cfg.token,
        timeout=cfg.timeout,
        verify_ssl=cfg.verify_ssl,
        log_level=cfg.log_level,
    )


def run_async(coro):
    import asyncio
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


def print_http_error(e: Exception, *, verbose: bool = False) -> None:
    """
    Pretty-print HTTP errors raised by your client's error_from_status.
    Expects attributes like .details (dict), .path, .status_code if available.
    """
    details: Optional[dict] = getattr(e, "details", None)
    path: Optional[str] = getattr(e, "path", None)
    status_code = getattr(e, "status_code", None) or getattr(e, "http_status", None)

    if isinstance(details, dict):
        msg = details.get("message") or str(e)
        http = details.get("httpStatus") or (f"HTTP {status_code}" if status_code else "HTTP error")
        _console.print(f"[red]{http}[/red]: {msg}" + (f" [dim]({path})[/dim]" if path else ""))
        # Summarize import report if present
        resp = details.get("response") or {}
        reports = resp.get("errorReports") or []
        if reports:
            r0 = reports[0]
            prop = r0.get("errorProperty") or (r0.get("errorProperties") or [None])[0]
            rmsg = r0.get("message") or "Validation error"
            if prop:
                _console.print(f"• {prop}: {rmsg}")
            else:
                _console.print(f"• {rmsg}")
        if verbose:
            # import here to avoid cycles
            from .output import _to_plain
            _console.rule("Full error details")
            try:
                _console.print_json(data=_to_plain(details))
            except Exception:
                _console.print(details)
    else:
        _console.print(f"[red]Error:[/red] {e}")
