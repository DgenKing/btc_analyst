from __future__ import annotations

from datetime import datetime, time, timezone


def active_sessions(now_utc: datetime | None = None) -> list[str]:
    now_utc = now_utc or datetime.now(timezone.utc)
    t = now_utc.time()
    active: list[str] = []
    if time(0, 0) <= t < time(9, 0):
        active.append("tokyo")
    if time(7, 0) <= t < time(16, 0):
        active.append("london")
    if time(12, 0) <= t < time(21, 0):
        active.append("ny")
    if time(12, 0) <= t < time(16, 0):
        active.append("london_ny_overlap")
    return active


def session_quality_multiplier(now_utc: datetime | None = None) -> float:
    sess = active_sessions(now_utc)
    if "london_ny_overlap" in sess:
        return 1.15
    if "ny" in sess or "london" in sess:
        return 1.05
    if not sess:
        return 0.85
    return 1.0
