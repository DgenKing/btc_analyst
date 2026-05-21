from __future__ import annotations

from .registry import Zone
from btc_analyst.indicators.structure import find_swing_highs, find_swing_lows


def _band(level: float, width_pct: float = 0.1) -> tuple[float, float]:
    w = float(level) * (width_pct / 100.0)
    return float(level) - w, float(level) + w


def _unswept_highs(df):
    highs = find_swing_highs(df['high'].astype(float).tolist(), 3)
    out = []
    if not highs:
        return out
    max_future = df['high'].astype(float).cummax().tolist()
    for idx, price in highs[-200:]:
        future_max = max(max_future[idx:]) if idx < len(max_future) else float(price)
        if future_max <= float(price):
            out.append(float(price))
    return out


def _unswept_lows(df):
    lows = find_swing_lows(df['low'].astype(float).tolist(), 3)
    out = []
    if not lows:
        return out
    min_future = df['low'].astype(float).cummin().tolist()
    for idx, price in lows[-200:]:
        future_min = min(min_future[idx:]) if idx < len(min_future) else float(price)
        if future_min >= float(price):
            out.append(float(price))
    return out


def detect_liquidity_zones(df_1h, current_price: float, symbol: str = 'BTCUSDT'):
    if df_1h is None or df_1h.empty or current_price <= 0:
        return []

    out = []
    low = float(current_price) * 0.95
    high = float(current_price) * 1.05
    start = int(low // 1000) * 1000
    end = int(high // 1000) * 1000

    for level in range(start, end + 1, 1000):
        zl, zh = _band(float(level), width_pct=0.1)
        zone_type = 'resistance' if float(level) > float(current_price) else 'support'
        out.append(
            Zone(
                symbol,
                zl,
                zh,
                zone_type,
                'liquidity',
                '1h',
                factors={'liquidity_strength': 0.4, 'liquidity_type': 'round_number'},
            )
        )

    for level in _unswept_highs(df_1h):
        zl, zh = _band(level, width_pct=0.1)
        out.append(
            Zone(
                symbol,
                zl,
                zh,
                'resistance',
                'liquidity',
                '1h',
                factors={'liquidity_strength': 0.7, 'liquidity_type': 'unswept_high'},
            )
        )

    for level in _unswept_lows(df_1h):
        zl, zh = _band(level, width_pct=0.1)
        out.append(
            Zone(
                symbol,
                zl,
                zh,
                'support',
                'liquidity',
                '1h',
                factors={'liquidity_strength': 0.7, 'liquidity_type': 'unswept_low'},
            )
        )

    return out
