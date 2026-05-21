import pandas as pd

from btc_analyst.indicators.structure import trend_label


def _flatish_df(n=80):
    closes = [100.0 + ((i % 4) - 2) * 0.15 for i in range(n)]
    highs = [c + 0.4 for c in closes]
    lows = [c - 0.4 for c in closes]
    return pd.DataFrame({'close': closes, 'high': highs, 'low': lows})


def test_trend_label_stable_sideways_for_daily_and_weekly():
    df = _flatish_df()
    assert trend_label(df, '1d') == 'sideways'
    assert trend_label(df, '1w') == 'sideways'
