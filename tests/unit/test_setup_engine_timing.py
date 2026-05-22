from datetime import datetime, timezone

from btc_analyst.setups.engine import _weekly_timing_quality


def test_weekly_timing_quality_windows_follow_framework_cycle():
    """Framework rule: Sunday preferred window starts at ~22:00 UTC; Mon/Tue preferred; Fri/Sat de-risked."""
    sun_preopen = _weekly_timing_quality(datetime(2026, 5, 24, 21, 59, tzinfo=timezone.utc))
    sun_open = _weekly_timing_quality(datetime(2026, 5, 24, 22, 0, tzinfo=timezone.utc))
    mon = _weekly_timing_quality(datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc))
    tue = _weekly_timing_quality(datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc))
    wed = _weekly_timing_quality(datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc))
    thu = _weekly_timing_quality(datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc))
    fri = _weekly_timing_quality(datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc))
    sat = _weekly_timing_quality(datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc))

    assert sun_preopen == ("midweek_window", 0.8)
    assert sun_open == ("optimal_window", 1.0)
    assert mon == ("optimal_window", 1.0)
    assert tue == ("optimal_window", 1.0)

    assert wed == ("midweek_window", 0.8)
    assert thu == ("late_week_window", 0.6)

    assert fri == ("late_week_window", 0.6)
    assert sat == ("late_week_window", 0.6)


def test_weekly_timing_quality_de_risks_thursday_like_friday():
    """Framework rule: Thursday/Friday reduce exposure before weekend, so Thursday should be late-week window."""
    thu = _weekly_timing_quality(datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc))
    fri = _weekly_timing_quality(datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc))

    assert thu == ("late_week_window", 0.6)
    assert fri == ("late_week_window", 0.6)
