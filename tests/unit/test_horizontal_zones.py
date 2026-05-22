import pandas as pd

from btc_analyst.zones.horizontal import detect_horizontal_zones


def test_horizontal_zone_strength_reflects_repeated_touches():
    """Framework Horizontal Trendlines: historical price agreement (repeated touches) should strengthen horizontal S/R."""
    n = 120
    base = [100 + (i * 0.03) for i in range(n)]

    # Repeated swing-high touches near the same level to encode strong historical agreement.
    highs = []
    lows = []
    closes = []
    for i, b in enumerate(base):
        if i % 12 in (0, 1, 2):
            high = 120.0  # repeated resistance area
        else:
            high = b + 1.2
        low = b - 1.0
        close = b + 0.1
        highs.append(high)
        lows.append(low)
        closes.append(close)

    df = pd.DataFrame(
        {
            "open_time": list(range(n)),
            "high": highs,
            "low": lows,
            "close": closes,
        }
    )

    zones = detect_horizontal_zones(df, timeframe="4h", symbol="BTCUSDT")
    resistance = [z for z in zones if z.zone_type == "resistance"]

    assert resistance, "Expected at least one horizontal resistance zone"
    assert any(float(z.factors.get("touches", 0)) >= 4 for z in resistance)
    assert any(float(z.factors.get("horizontal_strength", 0.0)) == 1.0 for z in resistance)
