
def detect_trigger(candle, zone, reaction):
    if not reaction: return None
    if zone['zone_type']=='support' and candle['close'] >= zone['price_low']:
        return '4h_close_reclaim'
    if zone['zone_type']=='resistance' and candle['close'] <= zone['price_high']:
        return '4h_close_reject'
    return None
