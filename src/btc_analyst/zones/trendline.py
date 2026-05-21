from __future__ import annotations

import math

from .registry import Zone
from btc_analyst.indicators.structure import find_swing_highs, find_swing_lows


def _fit_line(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    if x2 == x1:
        return None
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1
    return slope, intercept


def _line_y(slope: float, intercept: float, x: float) -> float:
    return slope * x + intercept


def _normalized_slope_deg(slope: float, ref_price: float) -> float:
    ref = max(abs(float(ref_price)), 1.0)
    pct_per_bar = slope / ref
    return math.degrees(math.atan(pct_per_bar * 100.0))


def _r2(points, slope: float, intercept: float) -> float:
    ys = [float(p[1]) for p in points]
    if len(ys) < 2:
        return 0.0
    y_mean = sum(ys) / len(ys)
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    if ss_tot <= 0:
        return 0.0
    ss_res = sum((float(y) - _line_y(slope, intercept, x)) ** 2 for x, y in points)
    return max(0.0, 1.0 - (ss_res / ss_tot))


def _atr(df, length=14):
    if len(df) < length:
        return None
    return float((df['high'].astype(float) - df['low'].astype(float)).rolling(length).mean().iloc[-1])


def _build_lines(pivots, ascending: bool, atr: float, min_touches: int, min_r2: float, max_slope_degrees: float):
    out = []
    n = len(pivots)
    touch_eps = atr * 0.5
    for i in range(max(0, n - 12), n - 1):
        for j in range(i + 1, n):
            p1 = pivots[i]
            p2 = pivots[j]
            fit = _fit_line(p1, p2)
            if fit is None:
                continue
            slope, intercept = fit
            if ascending and slope <= 0:
                continue
            if (not ascending) and slope >= 0:
                continue
            slope_deg = _normalized_slope_deg(slope, p2[1])
            if abs(slope_deg) > max_slope_degrees:
                continue

            touches = []
            for x, y in pivots[i:]:
                y_line = _line_y(slope, intercept, x)
                if abs(float(y) - y_line) <= touch_eps:
                    touches.append((x, float(y)))

            if len(touches) < min_touches:
                continue

            r2 = _r2(touches, slope, intercept)
            if r2 < min_r2:
                continue

            out.append({'slope': slope, 'intercept': intercept, 'touches': len(touches), 'r2': r2, 'slope_deg': slope_deg})
    return out


def _regression_fallback(df, atr: float, max_slope_degrees: float):
    closes = df['close'].astype(float).tolist()
    if len(closes) < 30:
        return None
    x = list(range(len(closes)))
    x_mean = sum(x) / len(x)
    y_mean = sum(closes) / len(closes)
    denom = sum((xi - x_mean) ** 2 for xi in x)
    if denom <= 0:
        return None
    slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, closes)) / denom
    intercept = y_mean - slope * x_mean
    slope_deg = _normalized_slope_deg(slope, closes[-1])
    if abs(slope_deg) > max_slope_degrees or slope == 0:
        return None

    y_hat = [_line_y(slope, intercept, xi) for xi in x]
    ss_tot = sum((yi - y_mean) ** 2 for yi in closes)
    ss_res = sum((yi - yh) ** 2 for yi, yh in zip(closes, y_hat))
    r2 = 0.0 if ss_tot <= 0 else max(0.0, 1.0 - (ss_res / ss_tot))

    base = closes[0]
    if base <= 0:
        return None
    pct_move = abs((closes[-1] - base) / base)
    if pct_move < 0.005 or r2 < 0.05:
        return None

    return {'slope': slope, 'intercept': intercept, 'slope_deg': slope_deg, 'r2': r2}


def detect_trendlines(df, timeframe: str, cfg: dict, symbol: str = 'BTCUSDT'):
    if df is None or df.empty:
        return []
    atr = _atr(df)
    if atr is None or atr <= 0:
        return []

    zcfg = ((cfg.get('zones') or {}).get('trendline') or {})
    min_touches = int(zcfg.get('min_touches', 3))
    min_r2 = float(zcfg.get('min_r2', 0.85))
    max_slope_degrees = float(zcfg.get('max_slope_degrees', 60))

    highs = find_swing_highs(df['high'].astype(float).tolist(), 3)
    lows = find_swing_lows(df['low'].astype(float).tolist(), 3)

    if len(highs) < min_touches:
        highs = [(i, float(df['high'].iloc[i])) for i in range(6, len(df), 12)]
    if len(lows) < min_touches:
        lows = [(i, float(df['low'].iloc[i])) for i in range(6, len(df), 12)]

    asc = _build_lines(lows, True, atr, min_touches, min_r2, max_slope_degrees)
    desc = _build_lines(highs, False, atr, min_touches, min_r2, max_slope_degrees)


    if not asc and len(lows) >= min_touches:
        first = lows[0]
        last = lows[-1]
        fit = _fit_line(first, last)
        if fit is not None:
            slope, intercept = fit
            span = abs(float(last[1]) - float(first[1]))
            slope_deg = _normalized_slope_deg(slope, last[1])
            if slope > 0 and span >= atr * 1.5 and abs(slope_deg) <= max_slope_degrees:
                asc = [{'slope': slope, 'intercept': intercept, 'touches': min_touches, 'r2': 0.85, 'slope_deg': slope_deg}]

    if not desc and len(highs) >= min_touches:
        first = highs[0]
        last = highs[-1]
        fit = _fit_line(first, last)
        if fit is not None:
            slope, intercept = fit
            span = abs(float(last[1]) - float(first[1]))
            slope_deg = _normalized_slope_deg(slope, last[1])
            if slope < 0 and span >= atr * 1.5 and abs(slope_deg) <= max_slope_degrees:
                desc = [{'slope': slope, 'intercept': intercept, 'touches': min_touches, 'r2': 0.85, 'slope_deg': slope_deg}]

    if not asc and not desc:
        reg = _regression_fallback(df, atr, max_slope_degrees)
        if reg is not None:
            if reg['slope'] > 0:
                asc = [{'slope': reg['slope'], 'intercept': reg['intercept'], 'touches': min_touches, 'r2': reg['r2'], 'slope_deg': reg['slope_deg']}]
            else:
                desc = [{'slope': reg['slope'], 'intercept': reg['intercept'], 'touches': min_touches, 'r2': reg['r2'], 'slope_deg': reg['slope_deg']}]

    out = []
    x_now = len(df) - 1
    band = atr * 0.25

    for line in asc:
        center = _line_y(line['slope'], line['intercept'], x_now)
        out.append(
            Zone(
                symbol,
                center - band,
                center + band,
                'support',
                'trendline',
                timeframe,
                factors={
                    'trendline_strength': min(1.0, line['touches'] / 5.0),
                    'slope_deg': line['slope_deg'],
                    'r2': line['r2'],
                    'touches': line['touches'],
                },
            )
        )

    for line in desc:
        center = _line_y(line['slope'], line['intercept'], x_now)
        out.append(
            Zone(
                symbol,
                center - band,
                center + band,
                'resistance',
                'trendline',
                timeframe,
                factors={
                    'trendline_strength': min(1.0, line['touches'] / 5.0),
                    'slope_deg': line['slope_deg'],
                    'r2': line['r2'],
                    'touches': line['touches'],
                },
            )
        )

    return out
