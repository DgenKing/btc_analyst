from btc_analyst.zones.registry import Zone
from btc_analyst.scoring.scorer import score_zone


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
