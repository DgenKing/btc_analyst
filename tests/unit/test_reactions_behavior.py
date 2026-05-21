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
