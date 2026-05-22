from btc_analyst.setups.reactions import detect_reactions


def test_resistance_rejection_requires_zone_contact_before_signaling_rejection():
    """Framework rule: bearish rejection is only valid when price interacts with resistance before signaling rejection."""
    resistance = {"zone_type": "resistance", "price_low": 108.0, "price_high": 110.0}

    prev_above = {"open": 110.8, "high": 111.0, "low": 110.4, "close": 110.6}
    close_below = {"open": 110.2, "high": 110.3, "low": 109.5, "close": 109.8}

    # Contact + close back under resistance should register a bearish rejection reaction.
    assert detect_reactions(close_below, prev_above, resistance) == "touch_reject"

    far_from_zone = {"open": 106.0, "high": 106.2, "low": 105.8, "close": 106.0}
    # If price never interacts with the resistance area, no rejection signal should be emitted.
    assert detect_reactions(far_from_zone, prev_above, resistance) is None


def test_bearish_rejection_rsi_signal_requires_weak_momentum_threshold():
    """Framework rule: bearish rejection quality should align with weak momentum at resistance."""
    resistance = {"zone_type": "resistance", "price_low": 108.0, "price_high": 110.0}
    prev_inside = {"open": 109.9, "high": 110.0, "low": 109.6, "close": 109.8}

    # Near resistance with weak momentum should emit RSI-based rejection.
    weak_momentum = {"open": 109.85, "high": 109.95, "low": 109.7, "close": 109.9}
    assert detect_reactions(weak_momentum, prev_inside, resistance, rsi=55.0, macd_hist=None) == "rsi_reject"

    # Same location but stronger momentum should not emit bearish RSI rejection.
    stronger_momentum = {"open": 109.85, "high": 109.95, "low": 109.7, "close": 109.9}
    assert detect_reactions(stronger_momentum, prev_inside, resistance, rsi=56.0, macd_hist=None) is None


def test_bullish_acceptance_rsi_reclaim_requires_minimum_rsi_at_support():
    """Framework rule: bullish acceptance should require reclaim-strength momentum at support."""
    support = {"zone_type": "support", "price_low": 100.0, "price_high": 102.0}
    prev_inside = {"open": 100.4, "high": 100.8, "low": 100.2, "close": 100.5}

    # Near support with reclaim-strength momentum should emit RSI-based bullish reclaim.
    reclaim_momentum = {"open": 100.29, "high": 100.45, "low": 100.285, "close": 100.3}
    assert detect_reactions(reclaim_momentum, prev_inside, support, rsi=45.0, macd_hist=None) == "rsi_reclaim"

    # Same location with weaker momentum should not emit RSI-based reclaim.
    weak_momentum = {"open": 100.29, "high": 100.45, "low": 100.285, "close": 100.3}
    assert detect_reactions(weak_momentum, prev_inside, support, rsi=44.9, macd_hist=None) is None
