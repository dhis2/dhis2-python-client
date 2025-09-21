from typing import Any, Dict, Optional

Json = Dict[str, Any]


def infer_item_key(data: Json) -> Optional[str]:
    for k, v in data.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return k
    for k, v in data.items():
        if isinstance(v, list):
            return k
    return None
