import numpy as np
import pandas as pd

from btc_analyst.analysis.probability import _signal_trend


def _df_from_close(close_values):
    return pd.DataFrame({"close": close_values})


def test_signal_trend_does_not_mark_bullish_stack_without_sma100_ordering():
    # price > SMA20 > SMA50 holds, but SMA100 is below SMA200, so full bullish stack
    # (which requires SMA100 between SMA50 and SMA200) must not trigger +0.9.
    close = [220.0] * 100 + [60.0] * 50 + list(np.linspace(240.0, 320.0, 50))
    score = _signal_trend(_df_from_close(close))
    assert score == 0.35


def test_signal_trend_does_not_mark_bearish_stack_without_sma100_ordering():
    # price < SMA20 < SMA50 holds, but SMA100 is above SMA200, so full bearish stack
    # (which requires SMA100 between SMA50 and SMA200) must not trigger -0.9.
    close = [80.0] * 100 + [260.0] * 50 + list(np.linspace(140.0, 60.0, 50))
    score = _signal_trend(_df_from_close(close))
    assert score == -0.35
