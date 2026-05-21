from btc_analyst.zones.registry import Zone
from btc_analyst.scoring.scorer import invalidated_by_rule, score_zone


def test_score_zone_basic():
    cfg = {
        "scoring": {
            "weights": {
                "horizontal_sr": 25,
                "volume_profile": 20,
                "ma_confluence": 10,
                "market_structure": 15,
            },
            "tier_thresholds": {"strong": 80, "medium": 60, "weak": 40},
            "multipliers": {"trend_with": 1.15},
        }
    }
    z = Zone("BTCUSDT", 100, 101, "support", "horizontal", "4h")
    z = score_zone(z, cfg, {"regime": "range"})
    assert z.score > 0


def test_horizontal_levels_outweigh_trendline_when_strength_is_equal():
    """Framework rule: horizontal levels carry higher importance than diagonal trendlines."""
    cfg = {
        "scoring": {
            "weights": {
                "horizontal_sr": 25,
                "trendline": 10,
                "crowd_positioning_extreme": 0,
            },
            "tier_thresholds": {"strong": 80, "medium": 60, "weak": 40},
            "multipliers": {
                "range_edge": 1.0,
                "range_mid": 1.0,
                "weekend": 1.0,
                "sunday_monday_tuesday": 1.0,
                "friday_saturday": 1.0,
            },
            "session_quality_weight": 0,
        }
    }

    ms = {"regime": "range", "weekday": 2}

    horizontal = Zone("BTCUSDT", 100, 101, "support", "horizontal", "4h")
    horizontal.factors = {"range_edge": True, "horizontal_strength": 1.0}
    horizontal = score_zone(horizontal, cfg, ms)

    diagonal = Zone("BTCUSDT", 100, 101, "support", "trendline", "4h")
    diagonal.factors = {"range_edge": True, "trendline_strength": 1.0}
    diagonal = score_zone(diagonal, cfg, ms)

    assert horizontal.score > diagonal.score


def test_weekly_cycle_multiplier_prefers_sunday_and_penalizes_friday_saturday():
    """Framework weekly cycle: Sunday setup window preferred; Friday/Saturday de-risked."""
    cfg = {
        "scoring": {
            "weights": {
                "horizontal_sr": 25,
                "crowd_positioning_extreme": 0,
            },
            "tier_thresholds": {"strong": 80, "medium": 60, "weak": 40},
            "multipliers": {
                "range_edge": 1.0,
                "range_mid": 1.0,
                "weekend": 1.0,
                "sunday_monday_tuesday": 1.10,
                "friday_saturday": 0.85,
            },
            "session_quality_weight": 0,
        }
    }

    def _mk_zone():
        z = Zone("BTCUSDT", 100, 101, "support", "horizontal", "4h")
        z.factors = {"range_edge": True, "horizontal_strength": 1.0}
        return z

    sun = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 6}).score
    wed = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 2}).score
    fri = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 4}).score

    assert sun > wed > fri


def test_weekly_cycle_preferred_window_treats_sunday_monday_tuesday_equally():
    """Framework weekly cycle: Sunday/Monday/Tuesday share the preferred setup window."""
    cfg = {
        "scoring": {
            "weights": {
                "horizontal_sr": 25,
                "crowd_positioning_extreme": 0,
            },
            "tier_thresholds": {"strong": 80, "medium": 60, "weak": 40},
            "multipliers": {
                "range_edge": 1.0,
                "range_mid": 1.0,
                "weekend": 1.0,
                "sunday_monday_tuesday": 1.10,
                "friday_saturday": 0.85,
            },
            "session_quality_weight": 0,
        }
    }

    def _mk_zone():
        z = Zone("BTCUSDT", 100, 101, "support", "horizontal", "4h")
        z.factors = {"range_edge": True, "horizontal_strength": 1.0}
        return z

    sun = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 6}).score
    mon = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 0}).score
    tue = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 1}).score

    assert sun == mon == tue


def test_acceptance_rejection_invalidation_requires_close_beyond_zone_and_atr_body():
    """Framework rule: acceptance/rejection invalidation needs a close beyond level with decisive body (> ATR)."""
    zone = {"price_low": 100.0, "price_high": 110.0}

    # Beyond resistance with strong impulse body: invalidated.
    breakout = {"open": 108.0, "close": 114.0}
    assert invalidated_by_rule(breakout, zone, atr4h=4.0) is True

    # Wick/weak body beyond level should not invalidate.
    weak_break = {"open": 112.2, "close": 113.0}
    assert invalidated_by_rule(weak_break, zone, atr4h=2.0) is False

    # Strong body but still inside the zone should not invalidate.
    inside_close = {"open": 101.0, "close": 107.0}
    assert invalidated_by_rule(inside_close, zone, atr4h=4.0) is False


def test_weekly_cycle_derisks_thursday_and_friday_before_weekend():
    """Framework weekly cycle: Thursday/Friday should reduce exposure relative to midweek neutral."""
    cfg = {
        "scoring": {
            "weights": {
                "horizontal_sr": 25,
                "crowd_positioning_extreme": 0,
            },
            "tier_thresholds": {"strong": 80, "medium": 60, "weak": 40},
            "multipliers": {
                "range_edge": 1.0,
                "range_mid": 1.0,
                "weekend": 1.0,
                "sunday_monday_tuesday": 1.10,
                "friday_saturday": 0.85,
            },
            "session_quality_weight": 0,
        }
    }

    def _mk_zone():
        z = Zone("BTCUSDT", 100, 101, "support", "horizontal", "4h")
        z.factors = {"range_edge": True, "horizontal_strength": 1.0}
        return z

    wed = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 2}).score
    thu = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 3}).score
    fri = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 4}).score

    assert wed > thu
    assert thu == fri


def test_weekly_cycle_derisks_saturday_equal_to_friday():
    """Framework weekly cycle: Friday and Saturday share the reduced-exposure bucket."""
    cfg = {
        "scoring": {
            "weights": {
                "horizontal_sr": 25,
                "crowd_positioning_extreme": 0,
            },
            "tier_thresholds": {"strong": 80, "medium": 60, "weak": 40},
            "multipliers": {
                "range_edge": 1.0,
                "range_mid": 1.0,
                "weekend": 1.0,
                "sunday_monday_tuesday": 1.10,
                "friday_saturday": 0.85,
            },
            "session_quality_weight": 0,
        }
    }

    def _mk_zone():
        z = Zone("BTCUSDT", 100, 101, "support", "horizontal", "4h")
        z.factors = {"range_edge": True, "horizontal_strength": 1.0}
        return z

    fri = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 4}).score
    sat = score_zone(_mk_zone(), cfg, {"regime": "range", "weekday": 5}).score

    assert sat == fri
