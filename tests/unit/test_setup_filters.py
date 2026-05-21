from btc_analyst.setups.filters import apply_hard_filters


def test_counter_trend_setup_requires_high_conviction_score_threshold():
    """Framework rule: leverage is only for high-conviction setups with strong confluence."""
    cfg = {
        "setups": {
            "min_rr_t1": 1.5,
            "atr_daily_max_pct": 5.0,
            "atr_daily_min_pct": 1.0,
        }
    }

    # Counter-trend setup below conviction threshold should be rejected.
    ok_low, reason_low = apply_hard_filters(
        rr_t1=2.0,
        cfg=cfg,
        atr_daily_pct=2.0,
        direction="long",
        zone_score=84,
        with_weekly_trend=False,
    )
    assert ok_low is False
    assert reason_low == "counter_trend_low_conviction"

    # Same setup at threshold should pass this gate.
    ok_high, reason_high = apply_hard_filters(
        rr_t1=2.0,
        cfg=cfg,
        atr_daily_pct=2.0,
        direction="long",
        zone_score=85,
        with_weekly_trend=False,
    )
    assert ok_high is True
    assert reason_high is None


def test_framework_supports_both_long_and_short_setup_directions():
    """Framework rule: trade direction includes both long and short, not long-only."""
    cfg = {
        "setups": {
            "min_rr_t1": 1.5,
            "atr_daily_max_pct": 5.0,
            "atr_daily_min_pct": 1.0,
        }
    }

    long_ok, long_reason = apply_hard_filters(rr_t1=2.0, cfg=cfg, direction="long", zone_score=90)
    short_ok, short_reason = apply_hard_filters(rr_t1=2.0, cfg=cfg, direction="short", zone_score=90)

    assert long_ok is True and long_reason is None
    assert short_ok is True and short_reason is None


def test_leverage_risk_control_blocks_crowded_funding_same_direction():
    """Framework rule: use leverage carefully and avoid crowded directional exposure."""
    cfg = {
        "setups": {
            "min_rr_t1": 1.5,
            "atr_daily_max_pct": 5.0,
            "atr_daily_min_pct": 1.0,
        }
    }

    ok, reason = apply_hard_filters(
        rr_t1=2.0,
        cfg=cfg,
        atr_daily_pct=2.0,
        direction="long",
        zone_score=90,
        with_weekly_trend=True,
        funding_extreme_same_direction=True,
        macro_event_window=False,
    )

    assert ok is False
    assert reason == "crowded_funding"
