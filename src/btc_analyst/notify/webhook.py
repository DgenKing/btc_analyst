from __future__ import annotations

import requests


def post_webhook(url: str, payload: dict, timeout: int = 10) -> bool:
    if not url:
        return False
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        return r.status_code < 300
    except Exception:
        return False
