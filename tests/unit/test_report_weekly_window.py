from datetime import datetime, timezone

import pytest

from btc_analyst.reports.daily import _weekly_trading_window


def test_weekly_trading_window_derisks_friday_into_exit_review_mode():
    """Framework rule: Friday should be close-out behavior, not fresh-entry mode."""
    friday = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)

    label, detail, color = _weekly_trading_window(friday)

    assert label == "Exit/review window"
    assert "Thursday/Friday" in detail
    assert color == "red"


def test_weekly_trading_window_marks_saturday_as_observation_only():
    """Framework rule: Saturday is observation-only, not active execution."""
    saturday = datetime(2026, 5, 23, 12, 0, tzinfo=timezone.utc)

    label, detail, color = _weekly_trading_window(saturday)

    assert label == "Observation-only window"
    assert "Saturday" in detail
    assert color == "red"


@pytest.mark.xfail(reason="Framework Sunday (10 PM GMT) timing not yet enforced in report weekly-window helper", strict=True)
def test_weekly_trading_window_gates_sunday_optimal_label_until_2200_utc():
    """Framework rule: Sunday setup/decision window starts when futures liquidity returns (~22:00 UTC)."""
    sunday_preopen = datetime(2026, 5, 24, 21, 59, tzinfo=timezone.utc)
    sunday_open = datetime(2026, 5, 24, 22, 0, tzinfo=timezone.utc)

    preopen_label, _, preopen_color = _weekly_trading_window(sunday_preopen)
    open_label, _, open_color = _weekly_trading_window(sunday_open)

    assert preopen_label == "Manage/selective window"
    assert preopen_color == "amber"
    assert open_label == "Optimal entry window"
    assert open_color == "green"
