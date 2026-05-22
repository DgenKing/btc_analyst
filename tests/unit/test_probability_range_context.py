import pandas as pd

from btc_analyst.analysis.probability import _signal_range_context


def test_range_context_scores_low_as_support_and_high_as_resistance_bias():
    """Framework rule: in a defined range, lower edge favors bullish support bias while upper edge favors bearish resistance bias."""
    # 50-candle range between 100 and 200 (high/low remain in the trailing window).
    scaffold = [100, 200] + [150] * 47

    near_low_df = pd.DataFrame({"close": scaffold + [100]})
    near_high_df = pd.DataFrame({"close": scaffold + [200]})
    mid_df = pd.DataFrame({"close": scaffold + [150]})

    assert _signal_range_context(near_low_df) == 0.5
    assert _signal_range_context(near_high_df) == -0.5
    assert _signal_range_context(mid_df) == 0.0
