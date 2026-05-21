from datetime import datetime, timezone

from btc_analyst.setups.engine import _weekly_timing_quality


def test_weekly_timing_quality_windows_follow_framework_cycle():
    """Framework rule: Sunday-Monday-Tuesday are preferred; Friday-Saturday are de-risked late-week windows."""
    sun = _weekly_timing_quality(datetime(2026, 5, 24, 22, 0, tzinfo=timezone.utc))
    mon = _weekly_timing_quality(datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc))
    tue = _weekly_timing_quality(datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc))
    wed = _weekly_timing_quality(datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc))
    thu = _weekly_timing_quality(datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc))
    fri = _weekly_timing_quality(datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc))
    sat = _weekly_timing_quality(datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc))

    assert sun == ("optimal_window", 1.0)
    assert mon == ("optimal_window", 1.0)
    assert tue == ("optimal_window", 1.0)

    assert wed == ("midweek_window", 0.8)
    assert thu == ("midweek_window", 0.8)

    assert fri == ("late_week_window", 0.6)
    assert sat == ("late_week_window", 0.6)
