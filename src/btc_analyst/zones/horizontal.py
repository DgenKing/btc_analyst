from __future__ import annotations

from .registry import Zone
from btc_analyst.indicators.structure import find_swing_highs, find_swing_lows


def _atr(df, length=14):
    if len(df) < length:
        return None
    return float((df['high'].astype(float) - df['low'].astype(float)).rolling(length).mean().iloc[-1])


def _touch_count(level: float, pivots: list[float], eps: float) -> int:
    return sum(1 for p in pivots if abs(float(p) - float(level)) <= eps)


def _age_days(df, pivot_idx: int) -> float:
    if 'open_time' not in df.columns:
        return 0.0
    ts = float(df['open_time'].iloc[pivot_idx])
    now = float(df['open_time'].iloc[-1])
    scale = 1000.0 if now > 10_000_000_000 else 1.0
    return max(0.0, (now - ts) / scale / 86400.0)


def detect_horizontal_zones(df, timeframe='4h', symbol='BTCUSDT'):
    highs = find_swing_highs(df['high'].astype(float).tolist(), 3)
    lows = find_swing_lows(df['low'].astype(float).tolist(), 3)
    out = []

    atr = _atr(df) or max(float(df['close'].astype(float).iloc[-1]) * 0.0025, 1.0)
    eps = atr * 0.3

    high_vals = [float(p) for _, p in highs]
    low_vals = [float(p) for _, p in lows]

    for idx, p in highs[-8:]:
        price = float(p)
        touches = _touch_count(price, high_vals, eps)
        age_days = _age_days(df, int(idx))
        out.append(
            Zone(
                symbol,
                price * 0.998,
                price * 1.002,
                'resistance',
                'horizontal',
                timeframe,
                factors={
                    'touches': touches,
                    'age_days': age_days,
                    'horizontal_strength': min(1.0, float(touches) / 4.0),
                },
            )
        )

    for idx, p in lows[-8:]:
        price = float(p)
        touches = _touch_count(price, low_vals, eps)
        age_days = _age_days(df, int(idx))
        out.append(
            Zone(
                symbol,
                price * 0.998,
                price * 1.002,
                'support',
                'horizontal',
                timeframe,
                factors={
                    'touches': touches,
                    'age_days': age_days,
                    'horizontal_strength': min(1.0, float(touches) / 4.0),
                },
            )
        )

    return out
