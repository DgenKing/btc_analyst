
def detect_trigger(candle, zone, reaction):
    if not reaction:
        return None

    if zone["zone_type"] == "support" and candle["close"] >= zone["price_low"]:
        sweep_low = candle.get("low")
        if sweep_low is not None and sweep_low >= zone["price_low"]:
            return None
        return "4h_close_reclaim"

    if zone["zone_type"] == "resistance" and candle["close"] <= zone["price_high"]:
        sweep_high = candle.get("high")
        if sweep_high is not None and sweep_high <= zone["price_high"]:
            return None
        return "4h_close_reject"

    return None
