def classify_regime(candles_daily):
    if len(candles_daily)<30: return 'range'
    first=float(candles_daily['close'].iloc[-30]); last=float(candles_daily['close'].iloc[-1]); change=(last-first)/first if first else 0
    atr=float((candles_daily['high']-candles_daily['low']).rolling(14).mean().iloc[-1]); atr_pct=atr/last if last else 0
    if atr_pct>0.05: return 'high_vol'
    if atr_pct<0.01: return 'low_vol'
    if change>0.05: return 'bull_trend'
    if change<-0.05: return 'bear_trend'
    return 'range'
