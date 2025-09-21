class DHIS2HTTPError(RuntimeError):
    def __init__(self, status_code: int, path: str, payload: dict | None):
        self.status_code = status_code
        self.path = path
        self.payload = payload or {}
        msg = _format_error(self.payload) or f"HTTP {status_code} on {path}"
        super().__init__(msg)


def _format_error(payload: dict) -> str:
    status = (
        (payload.get("response") or {}).get("status")
        or payload.get("status")
        or payload.get("httpStatus")
        or "UNKNOWN"
    )
    conflicts = (payload.get("response") or {}).get("conflicts") or payload.get("conflicts") or []
    if conflicts:
        parts = [
            f"{c.get('object', '?')}: {c.get('value') or c.get('message') or '?'}"
            for c in conflicts
        ]
        return f"{status}: {'; '.join(parts)}"
    message = payload.get("message") or payload.get("responseType")
    return f"{status}: {message}" if message else status
