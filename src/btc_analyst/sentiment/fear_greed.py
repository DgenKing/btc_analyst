from __future__ import annotations

import logging

from ._http import get_json

log = logging.getLogger(__name__)


def parse_fear_greed(payload: dict):
    rows = (payload or {}).get("data") or []
    if not rows:
        return None
    row = rows[0]
    return {
        "value": int(row.get("value")),
        "label": row.get("value_classification") or "Unknown",
        "ts": int(float(row.get("timestamp", 0) or 0)),
    }


def fetch_fear_greed(cache_ttl_seconds: int = 3600):
    try:
        payload = get_json("https://api.alternative.me/fng/", params={"limit": 30}, cache_ttl_seconds=cache_ttl_seconds)
        return parse_fear_greed(payload)
    except Exception as e:
        log.warning("fear&greed fetch failed: %s", e)
        return None
