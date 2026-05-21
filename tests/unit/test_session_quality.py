from datetime import datetime, timezone

from btc_analyst.context.sessions import session_quality_multiplier


def test_london_ny_overlap_has_higher_quality_than_single_session_windows():
    """Framework rule: prioritize high-confluence windows; London/NY overlap should rate above single-session periods."""
    tokyo_only = session_quality_multiplier(datetime(2026, 1, 5, 2, 0, tzinfo=timezone.utc))
    london_only = session_quality_multiplier(datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc))
    ny_only = session_quality_multiplier(datetime(2026, 1, 5, 18, 0, tzinfo=timezone.utc))
    overlap = session_quality_multiplier(datetime(2026, 1, 5, 13, 0, tzinfo=timezone.utc))

    assert overlap > london_only
    assert overlap > ny_only
    assert london_only > tokyo_only
    assert ny_only > tokyo_only
