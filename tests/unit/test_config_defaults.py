from btc_analyst.config import load_config


def test_default_timeframes_include_3d_for_daily_three_day_structure():
    """Framework Daily / 3-Day section requires 3d timeframe availability."""
    cfg = load_config()
    assert "3d" in cfg["data"]["timeframes"]
