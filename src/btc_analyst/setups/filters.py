
def apply_hard_filters(rr_t1, cfg, atr_daily_pct=None, direction='long', zone_score=0, with_weekly_trend=True, funding_extreme_same_direction=False, macro_event_window=False):
    if rr_t1 < cfg['setups']['min_rr_t1']: return False, 'rr_below_min'
    if atr_daily_pct is not None and atr_daily_pct > cfg['setups']['atr_daily_max_pct']: return False, 'atr_too_high'
    if atr_daily_pct is not None and atr_daily_pct < cfg['setups']['atr_daily_min_pct']: return False, 'atr_too_low'
    if (not with_weekly_trend) and zone_score < 85: return False, 'counter_trend_low_conviction'
    if funding_extreme_same_direction: return False, 'crowded_funding'
    if macro_event_window: return False, 'macro_event_window'
    if direction not in ('long','short'): return False, 'invalid_direction'
    return True, None
