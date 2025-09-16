from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Tuple

def extract_status(payload: dict) -> str:
    if payload.get("response", {}).get("status"):
        return payload["response"]["status"]
    if payload.get("status"):
        return payload["status"]
    if payload.get("httpStatus"):
        return payload["httpStatus"]
    return "UNKNOWN"

def extract_conflicts(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if payload.get("response", {}).get("conflicts"):
        return payload["response"]["conflicts"]
    if payload.get("conflicts"):
        return payload["conflicts"]
    return []

def dump_json(obj: Any) -> str:
    """
    Pretty-print an object as JSON (and return the string) to aid debugging
    during integration tests.
    """
    try:
        s = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        # Best-effort fallback if obj isn't JSON-serializable
        s = json.dumps({"_repr": repr(obj)}, ensure_ascii=False, indent=2, sort_keys=True)
    print(s)
    return s


def summarize_dvs_import(payload: Mapping[str, Any] | None) -> Tuple[str, Dict[str, Any]]:
    """
    Return (summary_line, compact_dict) for a dataValueSets import response.
    Handles common DHIS2 shapes:
      1) {"response": {"status": "...", "importCount": {...}, "conflicts": [...]}}
      2) {"status": "...", "stats": {...}, "conflicts": [...]}
      3) {"httpStatus": "...", "message": "...", "response": {...}}
    """

    if not payload:
        return (
            "status=UNKNOWN created=0 updated=0 deleted=0 ignored=0",
            {
                "status": "UNKNOWN",
                "created": 0,
                "updated": 0,
                "deleted": 0,
                "ignored": 0,
            },
        )

    # status
    status = extract_status(payload)

    # counts
    counts = (payload.get("response") or {}).get("importCount") or payload.get("stats") or {}
    created = int(counts.get("created", 0) or 0)
    updated = int(counts.get("updated", 0) or 0)
    deleted = int(counts.get("deleted", 0) or 0)
    ignored = int(counts.get("ignored", 0) or 0)

    # conflicts
    conflicts: List[Dict[str, Any]] = extract_conflicts(payload)
    conflicts_txt = "; ".join(
        f"{c.get('object', '?')}: {c.get('value') or c.get('message') or '?'}"
        for c in conflicts
    )

    # server message if present
    msg = payload.get("message") or (payload.get("response") or {}).get("description") or ""

    line = f"status={status} created={created} updated={updated} deleted={deleted} ignored={ignored}"
    if msg:
        line += f" message={msg}"
    if conflicts:
        line += f" conflicts=[{conflicts_txt}]"

    compact = {
        "status": status,
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "ignored": ignored,
    }
    if msg:
        compact["message"] = msg
    if conflicts:
        compact["conflicts"] = conflicts

    return line, compact
