from __future__ import annotations

import logging

from ._http import get_json

log = logging.getLogger(__name__)


def parse_okx_longshort(payload: dict):
    rows = (payload or {}).get("data") or []
    if not rows:
        return None
    row = rows[0]

    # OKX can return list rows: [ts, ratio]
    if isinstance(row, list) and len(row) >= 2:
        try:
            return {
                "long_short_ratio": float(row[1]),
                "ts": int(float(row[0] or 0)),
            }
        except Exception:
            return None

    if isinstance(row, dict):
        ratio = float(row.get("ratio") or row.get("longShortRatio") or 0)
        return {
            "long_short_ratio": ratio,
            "ts": int(float(row.get("ts", 0) or 0)),
        }

    return None


def fetch_okx_longshort(period: str = "1H", cache_ttl_seconds: int = 3600):
    """Fetch OKX BTC long/short account ratio.

    OKX supports period in {5m,1H,1D}; map common caller inputs safely.
    """
    period_map = {
        "5m": "5m", "15m": "5m", "30m": "5m",
        "1h": "1H", "1H": "1H", "2H": "1H", "4H": "1H", "6H": "1H", "8H": "1H", "12H": "1H",
        "1d": "1D", "1D": "1D",
    }
    okx_period = period_map.get(period, "1H")

    try:
        payload = get_json(
            "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio",
            params={"ccy": "BTC", "period": okx_period},
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*",
                "Referer": "https://www.okx.com/",
            },
            cache_ttl_seconds=cache_ttl_seconds,
        )
        # OKX can return code as string '0' for success
        if isinstance(payload, dict) and str(payload.get("code", "")) not in {"0", ""}:
            log.warning("okx long/short API non-success code=%s msg=%s", payload.get("code"), payload.get("msg"))
            return None
        return parse_okx_longshort(payload)
    except Exception as e:
        log.warning("okx long/short fetch failed: %s", e)
        return None
