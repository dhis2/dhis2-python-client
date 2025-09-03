from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Type


@dataclass
class DHIS2Error(Exception):
    """Base exception for DHIS2 client errors with optional HTTP context."""

    message: str
    status_code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    path: Optional[str] = None

    def __str__(self) -> str:
        base = f"{self.__class__.__name__}: {self.message}"
        if self.status_code is not None:
            base += f" (status={self.status_code})"
        if self.path:
            base += f" [path={self.path}]"
        return base


class AuthError(DHIS2Error): ...  # noqa: N818


class Forbidden(DHIS2Error): ...  # noqa: N818


class NotFound(DHIS2Error): ...  # noqa: N818


class BadRequest(DHIS2Error): ...  # noqa: N818


class Conflict(DHIS2Error): ...  # noqa: N818


class RateLimited(DHIS2Error): ...  # noqa: N818


class ServerError(DHIS2Error): ...  # noqa: N818


class NetworkError(DHIS2Error): ...  # noqa: N818


def error_from_status(
    status: int,
    message: str,
    *,
    path: Optional[str] = None,
    details: Optional[Dict] = None,
) -> DHIS2Error:
    """Map HTTP status to a typed exception, keeping the parsed payload (if any)."""
    mapping: Dict[int, Type[DHIS2Error]] = {
        400: BadRequest,
        401: AuthError,
        403: Forbidden,
        404: NotFound,
        409: Conflict,
        429: RateLimited,
    }
    exc = mapping.get(status)
    if exc is None:
        exc = ServerError if status >= 500 else DHIS2Error
    return exc(message=message, status_code=status, path=path, details=details)
