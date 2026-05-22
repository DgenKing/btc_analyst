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


def test_range_context_edge_thresholds_are_inclusive_and_nearby_values_do_not_trigger_edge_bias():
    """Framework rule: edge acceptance/rejection should trigger at exact range edges (10%/90%), while nearby non-edge values should not fire full edge bias."""
    # Keep trailing-window anchors fixed at [100, 200].
    scaffold = [100, 200] + [150] * 47

    exact_low_edge_df = pd.DataFrame({"close": scaffold + [110]})
    exact_high_edge_df = pd.DataFrame({"close": scaffold + [190]})
    just_above_low_edge_df = pd.DataFrame({"close": scaffold + [111]})
    just_below_high_edge_df = pd.DataFrame({"close": scaffold + [189]})

    # Positive cases: exact boundary should fire strong edge bias.
    assert _signal_range_context(exact_low_edge_df) == 0.5
    assert _signal_range_context(exact_high_edge_df) == -0.5

    # Negative cases: nearby values should be weaker than full edge responses.
    assert _signal_range_context(just_above_low_edge_df) != 0.5
    assert _signal_range_context(just_below_high_edge_df) != -0.5
