from datetime import datetime, timezone

from btc_analyst.analysis.probability import _score_probs, _signal_weekly_pattern


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


def test_probability_score_probs_applies_preferred_window_directional_boost_on_monday_and_tuesday():
    """Framework parity: preferred directional window is Sunday(post-open)/Monday/Tuesday, not Tuesday-only."""

    signal_vals = {"trend": 0.4, "weekly_pattern": 0.2}
    weights = {"trend": 0.7, "weekly_pattern": 0.3}

    monday_probs, _ = _score_probs(signal_vals, weights, weekday=0)
    tuesday_probs, _ = _score_probs(signal_vals, weights, weekday=1)
    wednesday_probs, _ = _score_probs(signal_vals, weights, weekday=2)

    assert monday_probs["up"] > wednesday_probs["up"]
    assert monday_probs["sideways"] < wednesday_probs["sideways"]

    assert tuesday_probs["up"] > wednesday_probs["up"]
    assert tuesday_probs["sideways"] < wednesday_probs["sideways"]


def test_probability_score_probs_derisks_friday_toward_sideways_vs_midweek():
    """Framework rule: Thursday/Friday should reduce exposure and avoid forcing directional setups."""

    signal_vals = {"trend": 0.4, "weekly_pattern": 0.2}
    weights = {"trend": 0.7, "weekly_pattern": 0.3}

    friday_probs, _ = _score_probs(signal_vals, weights, weekday=4)
    wednesday_probs, _ = _score_probs(signal_vals, weights, weekday=2)

    assert friday_probs["sideways"] > wednesday_probs["sideways"]
    assert friday_probs["up"] < wednesday_probs["up"]


def test_probability_score_probs_derisks_thursday_toward_sideways_vs_midweek():
    """Framework rule: Thursday/Friday should reduce exposure and avoid forcing directional setups."""

    signal_vals = {"trend": 0.4, "weekly_pattern": 0.2}
    weights = {"trend": 0.7, "weekly_pattern": 0.3}

    thursday_probs, _ = _score_probs(signal_vals, weights, weekday=3)
    wednesday_probs, _ = _score_probs(signal_vals, weights, weekday=2)

    assert thursday_probs["sideways"] > wednesday_probs["sideways"]
    assert thursday_probs["up"] < wednesday_probs["up"]
