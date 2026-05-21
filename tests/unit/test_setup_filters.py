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
