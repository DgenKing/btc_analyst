from __future__ import annotations

import time


def dedupe_key(kind, zone_id, ts):
    return f"{kind}:{zone_id}:{ts}"


def is_duplicate_within(conn, alert_type: str, zone_id: int, window_seconds: int) -> bool:
    since = int(time.time()) - int(window_seconds)
    row = conn.execute(
        "SELECT 1 FROM alerts WHERE alert_type=? AND zone_id=? AND created_at>=? LIMIT 1",
        (alert_type, int(zone_id), since),
    ).fetchone()
    return row is not None
