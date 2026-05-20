def _pct(a, b):
    if b == 0:
        return 999.0
    return abs(a - b) / abs(b) * 100.0


def detect_reactions(candle, prev_candle, zone, rsi=None, macd_hist=None, proximity_pct=0.35, wick_ratio_min=1.2):
    body = abs(candle['close'] - candle['open'])
    low_wick = min(candle['open'], candle['close']) - candle['low']
    high_wick = candle['high'] - max(candle['open'], candle['close'])

    close = float(candle['close'])
    low = float(candle['low'])
    high = float(candle['high'])
    zlow = float(zone['price_low'])
    zhigh = float(zone['price_high'])

    inside_zone = zlow <= close <= zhigh
    near_support = (_pct(close, zlow) <= proximity_pct) or (_pct(low, zlow) <= proximity_pct)
    near_resistance = (_pct(close, zhigh) <= proximity_pct) or (_pct(high, zhigh) <= proximity_pct)

    if zone['zone_type'] == 'support':
        if not (inside_zone or near_support):
            return None
        if low <= zlow and close >= zlow:
            return 'touch_reclaim'
        if low_wick > wick_ratio_min * max(body, 1e-9) and close >= zlow:
            return 'rejection_wick'
        if prev_candle and prev_candle['close'] < zlow and close > zlow:
            return 'failed_breakdown'
        if rsi is not None and rsi >= 45:
            return 'rsi_reclaim'
        if macd_hist is not None and macd_hist > 0:
            return 'macd_inflect'
    else:
        if not (inside_zone or near_resistance):
            return None
        if high >= zhigh and close <= zhigh:
            return 'touch_reject'
        if high_wick > wick_ratio_min * max(body, 1e-9) and close <= zhigh:
            return 'rejection_wick'
        if prev_candle and prev_candle['close'] > zhigh and close < zhigh:
            return 'failed_breakout'
        if rsi is not None and rsi <= 55:
            return 'rsi_reject'
        if macd_hist is not None and macd_hist < 0:
            return 'macd_inflect'
    return None
