from __future__ import annotations

import logging

from ._http import get_json

log = logging.getLogger(__name__)


def fetch_coingecko_context(cache_ttl_seconds: int = 3600):
    try:
        payload = get_json("https://api.coingecko.com/api/v3/global", cache_ttl_seconds=cache_ttl_seconds)
        d = (payload or {}).get("data") or {}
        mcp = d.get("market_cap_percentage") or {}
        return {
            "btc_dominance_pct": float(mcp.get("btc")) if mcp.get("btc") is not None else None,
            "total_market_cap_usd": ((d.get("total_market_cap") or {}).get("usd")),
            "total_volume_24h_usd": ((d.get("total_volume") or {}).get("usd")),
        }
    except Exception as e:
        log.warning("coingecko context fetch failed: %s", e)
        return None
