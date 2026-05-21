from btc_analyst.config import load_config


def test_default_timeframes_include_3d_for_daily_three_day_structure():
    """Framework Daily / 3-Day section requires 3d timeframe availability."""
    cfg = load_config()
    assert "3d" in cfg["data"]["timeframes"]


def test_default_derivatives_venue_tracks_hyperliquid_framework_instrument():
    """Framework primary trading instrument is BTC perpetuals on Hyperliquid."""
    cfg = load_config()
    assert cfg["data"]["derivatives_venue"] == "hyperliquid_perp"
