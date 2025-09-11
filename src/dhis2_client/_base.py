from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from .settings import Settings

DEFAULT_HEADERS: Dict[str, str] = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def _reveal(value):
    """Return plain string from SecretStr or pass through None/str."""
    if value is None:
        return None
    return value.get_secret_value() if hasattr(value, "get_secret_value") else value


def _get_auth_header_from_settings(settings: Settings) -> Dict[str, str]:
    """
    Support either a property or a method named 'auth_header' on Settings.
    """
    # property style
    try:
        v = settings.auth_header  # type: ignore[attr-defined]
        if isinstance(v, Mapping):
            return dict(v)
    except Exception:
        pass
    # method style
    try:
        maybe_callable = getattr(settings, "auth_header", None)
        if callable(maybe_callable):
            hdr = maybe_callable()
            if isinstance(hdr, Mapping):
                return dict(hdr)
    except Exception:
        pass
    return {}


class _ParamsMixin:
    """Shared param helpers for sync/async clients."""

    def _mk_params(
        self,
        fields: Iterable[str],
        page_size: int,
        paging: bool,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "fields": ",".join(fields),
            "pageSize": page_size,
            "paging": str(paging).lower(),
        }
        if extra_params:
            params.update(extra_params)
        return params
