from btc_analyst.reports.daily import _current_range


def test_current_range_rejects_levels_when_boundaries_are_too_far_from_price():
    """Framework rule: avoid forcing mid-range context when support/resistance are too distant from current market location."""
    current_price = 100_000.0
    support = [
        {"price_low": 84_900.0, "price_high": 85_100.0, "score": 95},
    ]
    resistance = [
        {"price_low": 114_900.0, "price_high": 115_100.0, "score": 96},
    ]

    result = _current_range(support, resistance, current_price)

    assert result == {"high": None, "low": None, "reason": "no_clear_range"}
