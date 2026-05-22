from datetime import datetime, timezone

from btc_analyst.reports.daily import _weekly_trading_window


def test_weekly_trading_window_derisks_friday_into_exit_review_mode():
    """Framework rule: Friday should be close-out behavior, not fresh-entry mode."""
    friday = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)

    label, detail, color = _weekly_trading_window(friday)

    assert label == "Exit/review window"
    assert "Thursday/Friday" in detail
    assert color == "red"
