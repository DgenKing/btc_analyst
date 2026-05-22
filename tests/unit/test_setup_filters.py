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


def test_only_long_or_short_directions_are_allowed_by_hard_filters():
    """Framework rule: primary trading direction is long/short only; other directions are invalid."""
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
        direction="flat",
        zone_score=90,
        with_weekly_trend=True,
    )

    assert ok is False
    assert reason == "invalid_direction"


def test_macro_event_window_blocks_new_setup_even_when_other_filters_pass():
    """Framework rule: preserve capital first and avoid forcing exposure in unstable conditions."""
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
        zone_score=95,
        with_weekly_trend=True,
        funding_extreme_same_direction=False,
        macro_event_window=True,
    )

    assert ok is False
    assert reason == "macro_event_window"


def test_atr_daily_risk_bounds_reject_setups_outside_allowed_volatility_window():
    """Framework rule: controlled risk requires volatility to stay inside configured ATR bounds before entry."""
    cfg = {
        "setups": {
            "min_rr_t1": 1.5,
            "atr_daily_max_pct": 5.0,
            "atr_daily_min_pct": 1.0,
        }
    }

    too_hot_ok, too_hot_reason = apply_hard_filters(
        rr_t1=2.0,
        cfg=cfg,
        atr_daily_pct=5.1,
        direction="long",
        zone_score=95,
        with_weekly_trend=True,
    )
    assert too_hot_ok is False
    assert too_hot_reason == "atr_too_high"

    too_cold_ok, too_cold_reason = apply_hard_filters(
        rr_t1=2.0,
        cfg=cfg,
        atr_daily_pct=0.9,
        direction="long",
        zone_score=95,
        with_weekly_trend=True,
    )
    assert too_cold_ok is False
    assert too_cold_reason == "atr_too_low"
