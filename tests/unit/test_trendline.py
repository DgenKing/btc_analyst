import pandas as pd

from btc_analyst.zones.trendline import detect_trendlines


def test_trendline_detects_support_on_ascending_structure():
    n = 120
    base = [100 + i * 0.35 for i in range(n)]
    highs = [v + (0.6 if i % 5 == 0 else 0.3) for i, v in enumerate(base)]
    lows = [v - (0.6 if i % 6 == 0 else 0.3) for i, v in enumerate(base)]
    closes = [v + (0.1 if i % 2 == 0 else -0.1) for i, v in enumerate(base)]
    df = pd.DataFrame({'open_time': list(range(n)), 'high': highs, 'low': lows, 'close': closes})
    cfg = {'zones': {'trendline': {'min_touches': 3, 'min_r2': 0.5, 'max_slope_degrees': 60}}}
    zones = detect_trendlines(df, timeframe='4h', cfg=cfg)
    assert any(z.zone_type == 'support' for z in zones)


def test_trendline_returns_empty_on_flat_noise():
    n = 120
    closes = [100 + ((i % 3) - 1) * 0.05 for i in range(n)]
    highs = [c + 0.1 for c in closes]
    lows = [c - 0.1 for c in closes]
    df = pd.DataFrame({'open_time': list(range(n)), 'high': highs, 'low': lows, 'close': closes})
    cfg = {'zones': {'trendline': {'min_touches': 3, 'min_r2': 0.85, 'max_slope_degrees': 60}}}
    zones = detect_trendlines(df, timeframe='4h', cfg=cfg)
    assert len(zones) == 0
