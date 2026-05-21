
from datetime import datetime, timezone

from .tiers import tier_from_score
from btc_analyst.context.sessions import active_sessions, session_quality_multiplier

def _clamp01(x):
    return max(0.0, min(1.0, float(x)))

def score_zone(zone,cfg,market_state=None):
    w=cfg['scoring']['weights']
    f=zone.factors or {}
    gw=lambda k, d=0.0: float(w.get(k, d))

    pts={
        'horizontal_sr': gw('horizontal_sr') * _clamp01(f.get('horizontal_strength', 1.0 if zone.source=='horizontal' else 0)),
        'volume_profile': gw('volume_profile') * _clamp01(f.get('vp_strength', 1.0 if zone.source.startswith('vp_') else 0)),
        'market_structure': gw('market_structure') * _clamp01(f.get('structure_align', 0.0)),
        'ma_confluence': gw('ma_confluence') * _clamp01(f.get('ma_strength', 1.0 if zone.source=='ma_cluster' else 0)),
        'trendline': gw('trendline') * _clamp01(f.get('trendline_strength', 0.0)),
        'liquidity': gw('liquidity') * _clamp01(f.get('liquidity_strength', 0.0)),
        'rsi_confirmation': gw('rsi_confirmation') * _clamp01(f.get('rsi_strength', 0.0)),
        'macd_confirmation': gw('macd_confirmation') * _clamp01(f.get('macd_strength', 0.0)),
        'funding_extreme': gw('funding_extreme') * _clamp01(f.get('funding_strength', 0.0)),
        'oi_delta': gw('oi_delta') * _clamp01(f.get('oi_strength', 0.0)),
        'cme_gap': gw('cme_gap') * _clamp01(f.get('cme_gap_strength', 1.0 if zone.source == 'cme_gap_proxy' else 0.0)),
        'liquidation_cluster_alignment': gw('liquidation_cluster_alignment') * _clamp01(f.get('liquidation_cluster_strength', 0.0)),
    }
    score=sum(pts.values())
    sessions = active_sessions(datetime.now(timezone.utc))
    session_mult = session_quality_multiplier(datetime.now(timezone.utc))
    session_weight = float(cfg.get('scoring', {}).get('session_quality_weight', 5))
    session_bonus = max(0.0, session_mult - 1.0) * session_weight * 10.0
    score += session_bonus

    crowd_weight = float(w.get('crowd_positioning_extreme', 5))
    crowd_label = (market_state or {}).get('crowd_aggregate_label', 'neutral')
    crowd_adjustment = 0.0
    if crowd_label == 'extreme_long_crowd':
        crowd_adjustment = crowd_weight if zone.zone_type in ('resistance',) else -crowd_weight
    elif crowd_label == 'extreme_short_crowd':
        crowd_adjustment = crowd_weight if zone.zone_type in ('support',) else -crowd_weight
    score += crowd_adjustment

    ms=market_state or {}
    regime=ms.get('regime','range')
    with_trend=bool(ms.get('with_trend', True))
    m = cfg['scoring'].get('multipliers', {})
    trend_with = float(m.get('trend_with', 1.15))
    trend_against = float(m.get('trend_against', 0.85))
    range_edge = float(m.get('range_edge', 1.10))
    range_mid = float(m.get('range_mid', 0.70))
    weekend_mult = float(m.get('weekend', 0.85))
    smt_mult = float(m.get('sunday_monday_tuesday', 1.10))
    fs_mult = float(m.get('friday_saturday', 0.85))

    if regime in ('bull_trend','bear_trend'):
        score *= trend_with if with_trend else trend_against
    elif regime=='range':
        score *= range_edge if bool(f.get('range_edge', False)) else range_mid

    if ms.get('is_weekend', False):
        score *= weekend_mult

    # weekly cycle timing multiplier
    weekday = ms.get('weekday')
    if weekday is None:
        weekday = datetime.now(timezone.utc).weekday()
    # Monday(0)-Tuesday(1)-Sunday(6) = preferred entry window
    if weekday in (6, 0, 1):
        score *= smt_mult
    # Thursday-Friday-Saturday = reduced exposure window
    elif weekday in (3, 4, 5):
        score *= fs_mult

    # recency multiplier, modeled from spec bins
    age_days=float(f.get('age_days', 0))
    if age_days > 60: score *= 0.70
    elif age_days >= 14: score *= 0.85

    zone.score=min(100, round(score, 2))
    zone.tier=tier_from_score(zone.score,cfg)
    zone.factors={**f, 'score_breakdown':pts, 'crowd_positioning_adjustment': crowd_adjustment, 'session_quality_multiplier': session_mult, 'active_sessions': sessions}
    return zone

def invalidated_by_rule(candle_4h, zone, atr4h):
    low,high=zone['price_low'],zone['price_high']
    close=candle_4h['close']; body=abs(candle_4h['close']-candle_4h['open'])
    if close > high and body > atr4h: return True
    if close < low and body > atr4h: return True
    return False
