import pytest

from btc_analyst.setups.triggers import detect_trigger


def test_trigger_requires_liquidity_sweep_confirmation_before_support_reclaim():
    """Framework rule: 1H entry should include a liquidity sweep before confirming a support reclaim trigger."""
    support = {"zone_type": "support", "price_low": 100.0, "price_high": 102.0}

    candle_without_sweep = {"open": 101.2, "high": 101.5, "low": 100.3, "close": 100.8}
    candle_with_sweep = {"open": 99.8, "high": 101.1, "low": 99.6, "close": 100.7}

    # Without a sweep below support, reclaim trigger should stay inactive.
    assert detect_trigger(candle_without_sweep, support, reaction=True) is None
    # With a sweep below support and close reclaimed, trigger can activate.
    assert detect_trigger(candle_with_sweep, support, reaction=True) == "4h_close_reclaim"


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
