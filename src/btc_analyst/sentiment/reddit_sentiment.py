from __future__ import annotations

import logging

from ._http import get_json

log = logging.getLogger(__name__)


def fetch_reddit_sentiment(user_agent: str = "btc_analyst/1.0 by /u/your_reddit_handle", cache_ttl_seconds: int = 3600):
    # Rough proxy only. Optional source.
    subs = ["BitcoinMarkets", "CryptoCurrency"]
    weights = {"bull": 1, "long": 1, "moon": 1, "pump": 1, "bear": -1, "short": -1, "dump": -1, "crash": -1}
    score = 0.0
    count = 0
    for s in subs:
        try:
            payload = get_json(
                f"https://www.reddit.com/r/{s}/hot.json",
                params={"limit": 25},
                headers={"User-Agent": user_agent},
                cache_ttl_seconds=cache_ttl_seconds,
            )
            posts = (((payload or {}).get("data") or {}).get("children") or [])
            for p in posts:
                d = p.get("data") or {}
                title = (d.get("title") or "").lower()
                ups = float(d.get("ups") or 1)
                for k, w in weights.items():
                    if k in title:
                        score += w * max(1.0, ups ** 0.5)
                count += 1
        except Exception as e:
            log.warning("reddit sentiment fetch failed for r/%s: %s", s, e)
    if count == 0:
        return None
    return {"score": round(score / max(count, 1), 4), "sample_size": count, "note": "heuristic_proxy"}
