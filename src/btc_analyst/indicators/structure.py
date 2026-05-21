from __future__ import annotations

import pandas as pd


def find_swing_highs(highs, N):
    out = []
    for i in range(N, len(highs) - N):
        if highs[i] == max(highs[i - N:i + N + 1]):
            out.append((i, highs[i]))
    return out


def find_swing_lows(lows, N):
    out = []
    for i in range(N, len(lows) - N):
        if lows[i] == min(lows[i - N:i + N + 1]):
            out.append((i, lows[i]))
    return out


def classify_structure(swings):
    if len(swings) < 4:
        return "sideways"
    vals = [p for _, p in swings[-4:]]
    return "HH-HL" if vals[-1] > vals[-2] else "LH-LL"


def _structure_direction(df: pd.DataFrame) -> str:
    highs = find_swing_highs(df['high'].astype(float).tolist(), 2)
    lows = find_swing_lows(df['low'].astype(float).tolist(), 2)
    if len(highs) < 2 or len(lows) < 2:
        return 'sideways'

    last_high = float(highs[-1][1])
    prev_high = float(highs[-2][1])
    last_low = float(lows[-1][1])
    prev_low = float(lows[-2][1])

    if last_high > prev_high and last_low > prev_low:
        return 'up'
    if last_high < prev_high and last_low < prev_low:
        return 'down'
    return 'sideways'


def trend_label(df: pd.DataFrame, timeframe: str) -> str:
    """Return 'up' | 'down' | 'sideways' using structure + EMA slope with TF-specific thresholds."""
    tf_rules = {
        '1w': {'lookback': 8, 'threshold': 0.03, 'ema_span': 20},
        '1d': {'lookback': 21, 'threshold': 0.02, 'ema_span': 20},
        '12h': {'lookback': 14, 'threshold': 0.015, 'ema_span': 20},
        '8h': {'lookback': 18, 'threshold': 0.012, 'ema_span': 20},
        '4h': {'lookback': 24, 'threshold': 0.01, 'ema_span': 20},
        '1h': {'lookback': 48, 'threshold': 0.006, 'ema_span': 50},
    }
    rule = tf_rules.get(str(timeframe).lower())
    if rule is None or df is None or df.empty or 'close' not in df.columns:
        return 'sideways'

    close = pd.to_numeric(df['close'], errors='coerce').dropna()
    lookback = int(rule['lookback'])
    if len(close) < lookback:
        return 'sideways'

    base = float(close.iloc[-lookback])
    if base <= 0:
        return 'sideways'

    current = float(close.iloc[-1])
    pct_change = (current - base) / base

    ema = close.ewm(span=int(rule['ema_span']), adjust=False).mean()
    if len(ema) < 2:
        return 'sideways'
    ema_slope = float(ema.iloc[-1] - ema.iloc[-2])
    ema_dir = 'up' if ema_slope > 0 else ('down' if ema_slope < 0 else 'sideways')

    if {'high', 'low'}.issubset(df.columns):
        structure_dir = _structure_direction(df[['high', 'low']].copy())
    else:
        structure_dir = 'sideways'

    if ema_dir in ('up', 'down') and ema_dir == structure_dir:
        return ema_dir

    threshold = float(rule['threshold'])
    pct_dir = 'up' if pct_change > threshold else ('down' if pct_change < -threshold else 'sideways')
    if pct_dir in ('up', 'down') and pct_dir == ema_dir:
        return pct_dir

    return 'sideways'
