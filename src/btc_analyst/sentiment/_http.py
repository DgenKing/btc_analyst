from __future__ import annotations

import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

log = logging.getLogger(__name__)
_CACHE: dict[tuple[str, str], tuple[float, Any]] = {}


def get_json(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 15,
    cache_ttl_seconds: int = 0,
    max_attempts: int = 3,
):
    q = ""
    if params:
        q = urllib.parse.urlencode(params)
    full_url = f"{url}?{q}" if q else url
    cache_key = (full_url, json.dumps(headers or {}, sort_keys=True))

    if cache_ttl_seconds > 0:
        hit = _CACHE.get(cache_key)
        if hit and (time.time() - hit[0]) < cache_ttl_seconds:
            return hit[1]

    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(full_url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if cache_ttl_seconds > 0:
                _CACHE[cache_key] = (time.time(), payload)
            return payload
        except urllib.error.HTTPError as e:
            # Do not retry hard client errors except throttling.
            if e.code not in (429, 500, 502, 503, 504):
                raise
            last_err = e
        except Exception as e:  # network/timeout/transient
            last_err = e

        if attempt < max_attempts:
            delay = (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            log.warning("get_json retrying attempt=%s url=%s after=%.2fs err=%s", attempt, full_url, delay, last_err)
            time.sleep(delay)

    raise last_err if last_err else RuntimeError(f"request failed: {full_url}")
