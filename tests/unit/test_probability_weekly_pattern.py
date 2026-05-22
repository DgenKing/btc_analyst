from datetime import datetime, timezone

from btc_analyst.analysis.probability import _signal_weekly_pattern


def test_probability_weekly_pattern_prefers_sunday_monday_tuesday_and_derisks_saturday():
    """Framework rule: Sunday (post-open), Monday, and Tuesday are preferred windows; Saturday is observation-only/de-risked."""

    # 2026-05-24 is Sunday, 2026-05-26 is Tuesday, 2026-05-30 is Saturday.
    sunday_ts = int(datetime(2026, 5, 24, 22, 0, tzinfo=timezone.utc).timestamp())
    monday_ts = int(datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc).timestamp())
    tuesday_ts = int(datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).timestamp())
    saturday_ts = int(datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc).timestamp())

    sunday = _signal_weekly_pattern(sunday_ts)
    monday = _signal_weekly_pattern(monday_ts)
    tuesday = _signal_weekly_pattern(tuesday_ts)
    saturday = _signal_weekly_pattern(saturday_ts)

    assert sunday > 0.0
    assert monday > 0.0
    assert tuesday > 0.0
    assert saturday == 0.0
    assert sunday == monday == tuesday


def test_probability_weekly_pattern_gates_sunday_until_2200_utc_open():
    """Framework timing nuance: Sunday boost starts only when futures/liquidity returns (~22:00 UTC)."""

    sunday_preopen_ts = int(datetime(2026, 5, 24, 21, 59, tzinfo=timezone.utc).timestamp())
    sunday_open_ts = int(datetime(2026, 5, 24, 22, 0, tzinfo=timezone.utc).timestamp())

    preopen = _signal_weekly_pattern(sunday_preopen_ts)
    open_window = _signal_weekly_pattern(sunday_open_ts)

    assert preopen == 0.0
    assert open_window > 0.0
