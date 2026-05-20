from __future__ import annotations

import logging

from ._http import get_json

log = logging.getLogger(__name__)


def parse_bybit_account_ratio(payload: dict):
    rows = ((payload or {}).get("result") or {}).get("list") or []
    if not rows:
        return None
    row = rows[0]
    buy = float(row.get("buyRatio", 0) or 0)
    sell = float(row.get("sellRatio", 0) or 0)
    ratio = (buy / sell) if sell > 0 else None
    return {
        "buy_ratio": buy,
        "sell_ratio": sell,
        "long_short_ratio": ratio,
        "ts": int(float(row.get("timestamp", 0) or 0)),
    }


def fetch_bybit_longshort(period: str = "4h", limit: int = 30, cache_ttl_seconds: int = 3600):
    try:
        payload = get_json(
            "https://api.bybit.com/v5/market/account-ratio",
            params={"category": "linear", "symbol": "BTCUSDT", "period": period, "limit": limit},
            cache_ttl_seconds=cache_ttl_seconds,
        )
        return parse_bybit_account_ratio(payload)
    except Exception as e:
        log.warning("bybit long/short fetch failed: %s", e)
        return None
