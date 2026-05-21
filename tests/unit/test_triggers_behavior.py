from btc_analyst.setups.triggers import detect_trigger


def test_trigger_requires_reaction_and_structure_confirmation_by_zone_type():
    """Framework rule: long needs support reclaim and short needs resistance rejection after reaction confirmation."""
    support = {"zone_type": "support", "price_low": 100.0, "price_high": 102.0}
    resistance = {"zone_type": "resistance", "price_low": 108.0, "price_high": 110.0}

    # No reaction signal means no trade trigger, even if close is above support.
    assert detect_trigger({"close": 101.0}, support, reaction=False) is None

    # Long-side confirmation requires reclaiming support.
    assert detect_trigger({"close": 100.0}, support, reaction=True) == "4h_close_reclaim"
    assert detect_trigger({"close": 99.9}, support, reaction=True) is None

    # Short-side confirmation requires rejection from resistance.
    assert detect_trigger({"close": 110.0}, resistance, reaction=True) == "4h_close_reject"
    assert detect_trigger({"close": 110.1}, resistance, reaction=True) is None
