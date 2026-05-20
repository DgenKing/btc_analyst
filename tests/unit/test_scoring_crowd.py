from btc_analyst.zones.registry import Zone
from btc_analyst.scoring.scorer import score_zone


def _cfg():
    return {
        "scoring": {
            "weights": {
                "horizontal_sr": 25,
                "volume_profile": 20,
                "ma_confluence": 10,
                "market_structure": 15,
                "crowd_positioning_extreme": 5,
            },
            "tier_thresholds": {"strong": 80, "medium": 60, "weak": 40},
            "multipliers": {"trend_with": 1.15, "range_mid": 1.0, "range_edge": 1.0},
        }
    }


def test_score_zone_crowd_extreme_long_penalizes_longs_boosts_shorts():
    cfg = _cfg()
    z_long = Zone("BTCUSDT", 100, 101, "support", "horizontal", "4h")
    z_short = Zone("BTCUSDT", 100, 101, "resistance", "horizontal", "4h")

    a = score_zone(z_long, cfg, {"regime": "range", "crowd_aggregate_label": "extreme_long_crowd"})
    b = score_zone(z_short, cfg, {"regime": "range", "crowd_aggregate_label": "extreme_long_crowd"})

    assert a.factors["crowd_positioning_adjustment"] == -5
    assert b.factors["crowd_positioning_adjustment"] == 5


def test_score_zone_mild_crowd_no_adjustment():
    cfg = _cfg()
    z = Zone("BTCUSDT", 100, 101, "support", "horizontal", "4h")
    a = score_zone(z, cfg, {"regime": "range", "crowd_aggregate_label": "mild_long"})
    assert a.factors["crowd_positioning_adjustment"] == 0
