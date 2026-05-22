from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from btc_analyst.analysis.heatmap import get_latest_heatmap
from btc_analyst.config import load_config
from btc_analyst.data.funding_store import fetch_funding
from btc_analyst.data.hyperliquid_client import HyperliquidClient
from btc_analyst.data.ohlcv_store import fetch_history
from btc_analyst.data.oi_store import fetch_oi

TIMEFRAMES = ("4h", "1d", "1w")

WEIGHTS = {
    "trending": {"trend": 0.22, "range_context": 0.05, "volume": 0.10, "volatility_state": 0.06, "sr_proximity": 0.10, "momentum": 0.18, "weekly_pattern": 0.05, "funding_oi": 0.10, "cvd": 0.10, "liq_clusters": 0.04},
    "ranging": {"trend": 0.08, "range_context": 0.22, "volume": 0.10, "volatility_state": 0.08, "sr_proximity": 0.20, "momentum": 0.12, "weekly_pattern": 0.06, "funding_oi": 0.07, "cvd": 0.05, "liq_clusters": 0.02},
    "low_vol_compression": {"trend": 0.10, "range_context": 0.18, "volume": 0.15, "volatility_state": 0.20, "sr_proximity": 0.12, "momentum": 0.08, "weekly_pattern": 0.05, "funding_oi": 0.05, "cvd": 0.05, "liq_clusters": 0.02},
    "volatile_chop": {"trend": 0.12, "range_context": 0.10, "volume": 0.12, "volatility_state": 0.15, "sr_proximity": 0.12, "momentum": 0.12, "weekly_pattern": 0.05, "funding_oi": 0.10, "cvd": 0.08, "liq_clusters": 0.04},
    "mixed": {"trend": 0.15, "range_context": 0.12, "volume": 0.10, "volatility_state": 0.08, "sr_proximity": 0.15, "momentum": 0.13, "weekly_pattern": 0.05, "funding_oi": 0.08, "cvd": 0.08, "liq_clusters": 0.06},
}

HORIZON_SEC = {"4h": 4 * 3600, "1d": 24 * 3600, "1w": 7 * 24 * 3600}
MOVE_THRESH = {"4h": 0.008, "1d": 0.015, "1w": 0.03}


@dataclass
class RegimeState:
    timeframe: str
    regime: str
    adx: float
    hurst: float
    atr_pct: float
    atr_regime: str
    bb_width_pct: float
    bb_squeeze: int
    confidence: float


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        (df["high"] - df["low"]).abs(),
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def _adx(df: pd.DataFrame, n: int = 14) -> float:
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = (high.diff()).clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(n).mean().replace(0, np.nan)
    plus_di = 100 * (plus_dm.rolling(n).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(n).mean() / atr)
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).replace([np.inf, -np.inf], np.nan)
    adx = dx.rolling(n).mean().iloc[-1]
    return float(0 if pd.isna(adx) else adx)


def _hurst(close: pd.Series, window: int = 200) -> float:
    x = close.dropna().tail(window).astype(float).values
    if len(x) < 50:
        return 0.5
    lags = range(2, min(50, len(x)//2))
    tau = [np.std(np.subtract(x[l:], x[:-l])) for l in lags]
    tau = np.array([t for t in tau if t > 0])
    if len(tau) < 10:
        return 0.5
    lagv = np.log(np.array(list(lags)[:len(tau)]))
    poly = np.polyfit(lagv, np.log(tau), 1)
    return float(np.clip(poly[0] * 2.0, 0.1, 0.9))


def _bb_width_pct(close: pd.Series, n: int = 20) -> tuple[float, int]:
    ma = close.rolling(n).mean()
    std = close.rolling(n).std(ddof=0)
    up, dn = ma + 2 * std, ma - 2 * std
    width = ((up - dn) / ma.replace(0, np.nan)) * 100
    w = width.iloc[-1]
    hist = width.dropna().tail(180)
    squeeze = int(len(hist) >= 20 and w <= hist.min())
    return (float(0 if pd.isna(w) else w), squeeze)


def _sma_slope(close: pd.Series, n: int = 50) -> float:
    sma = close.rolling(n).mean()
    if len(sma.dropna()) < 10:
        return 0.0
    a, b = float(sma.iloc[-1]), float(sma.iloc[-8])
    return 0.0 if b == 0 else (a - b) / b


def _classify_regime(adx: float, hurst: float, atr_regime: str, bb_squeeze: int, sma_slope: float) -> tuple[str, float]:
    if bb_squeeze and atr_regime == "low":
        return "low_vol_compression", 0.8
    if adx > 25 and hurst > 0.55:
        return ("trending_up" if sma_slope > 0 else "trending_down"), 0.85
    if adx < 20 and hurst < 0.45:
        return "ranging", 0.8
    if atr_regime == "high" and adx < 25:
        return "volatile_chop", 0.7
    return "mixed", 0.5


def _regime_weight_key(regime: str) -> str:
    if regime.startswith("trending_"):
        return "trending"
    return regime if regime in WEIGHTS else "mixed"


def _latest_df(conn, timeframe: str, venue: str) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT open_time,open,high,low,close,volume FROM candles WHERE symbol='BTCUSDT' AND venue=? AND timeframe=? ORDER BY open_time DESC LIMIT 420",
        conn,
        params=[venue, timeframe],
    ).sort_values("open_time")


def _signal_trend(df: pd.DataFrame) -> float:
    c = df["close"]
    sma20, sma50, sma100, sma200 = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(100).mean(), c.rolling(200).mean()
    p = float(c.iloc[-1])
    s = 0.0
    if p > sma20.iloc[-1] > sma50.iloc[-1] > sma100.iloc[-1] > sma200.iloc[-1]:
        s += 0.9
    elif p < sma20.iloc[-1] < sma50.iloc[-1] < sma100.iloc[-1] < sma200.iloc[-1]:
        s -= 0.9
    else:
        s += np.sign(p - sma50.iloc[-1]) * 0.35
    return float(np.clip(s, -1, 1))


def _signal_range_context(df: pd.DataFrame) -> float:
    c = df["close"]
    hi, lo = float(c.tail(50).max()), float(c.tail(50).min())
    p = float(c.iloc[-1])
    span = max(hi - lo, 1e-9)
    pos = (p - lo) / span
    if 0.4 <= pos <= 0.6:
        return 0.0
    if pos >= 0.9:
        return -0.5
    if pos <= 0.1:
        return 0.5
    return float(np.clip((pos - 0.5) * 1.2, -0.7, 0.7))


def _signal_volume(df: pd.DataFrame) -> float:
    last = df.iloc[-1]
    vr = float(last["volume"]) / max(float(df["volume"].tail(20).mean()), 1e-9)
    direction = 1 if float(last["close"]) >= float(last["open"]) else -1
    if vr > 1.5:
        return 0.7 * direction
    if vr < 0.7:
        return 0.1 * direction
    return 0.2 * direction


def _signal_volatility(df: pd.DataFrame, atr_regime: str, bb_squeeze: int) -> float:
    if bb_squeeze and atr_regime == "low":
        return 0.0
    if atr_regime == "high":
        return float(np.sign(float(df["close"].iloc[-1] - df["close"].iloc[-4])) * 0.4)
    return 0.0


def _signal_sr(conn, price: float) -> float:
    rows = conn.execute("SELECT price_low,price_high,zone_type,score FROM zones WHERE status='active' ORDER BY score DESC LIMIT 25").fetchall()
    if not rows:
        return 0.0
    best = min(rows, key=lambda r: abs(((float(r[0])+float(r[1]))/2.0)-price))
    mid = (float(best[0]) + float(best[1])) / 2.0
    dist = abs(price - mid) / max(price, 1e-9)
    if dist > 0.005:
        return 0.0
    return 0.7 if str(best[2]) == "support" else -0.7


def _signal_momentum(df: pd.DataFrame) -> float:
    c = df["close"]
    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan)
    rsi = 100 - (100/(1 + (up/dn)))
    r = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else 50
    rs = 0.6 if r < 30 else (-0.6 if r > 70 else (0.3 if 45 <= r <= 55 else 0.0))
    ema12 = c.ewm(span=12, adjust=False).mean(); ema26 = c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26; sig = macd.ewm(span=9, adjust=False).mean(); hist = macd - sig
    h0 = float(hist.iloc[-1]) if pd.notna(hist.iloc[-1]) else 0.0
    h1 = float(hist.iloc[-2]) if len(hist) >= 2 and pd.notna(hist.iloc[-2]) else h0
    ms = 0.5 if (h0 > 0 and h0 >= h1) else (-0.5 if (h0 < 0 and h0 <= h1) else (0.1 if h0 > 0 else -0.1))
    return float(np.clip(0.45 * rs + 0.55 * ms, -1, 1))


def _signal_weekly_pattern(ts: int) -> float:
    g = time.gmtime(ts)
    wd = g.tm_wday
    if wd == 5:
        return 0.0
    if wd == 6:
        return 0.2 if g.tm_hour >= 22 else 0.0
    if wd in (0, 1):
        return 0.2
    return 0.0


def _signal_funding_oi(conn) -> float:
    fr = conn.execute("SELECT funding_rate FROM funding WHERE venue='hyperliquid_perp' ORDER BY funding_time DESC LIMIT 1").fetchone()
    oi = conn.execute("SELECT oi FROM open_interest WHERE venue='hyperliquid_perp' ORDER BY ts DESC LIMIT 2").fetchall()
    if not fr:
        return 0.0
    f = float(fr[0])
    oi_ch = 0.0
    if len(oi) == 2 and float(oi[1][0]) != 0:
        oi_ch = (float(oi[0][0]) - float(oi[1][0])) / float(oi[1][0])
    if f > 0.001:
        return -0.7
    if f > 0.0005 and oi_ch > 0:
        return -0.5
    if f < -0.001:
        return 0.7
    if f < -0.0005 and oi_ch > 0:
        return 0.5
    return 0.0


def _signal_cvd() -> float:
    try:
        rows = HyperliquidClient().recent_trades('BTC') or []
    except Exception:
        return 0.0
    cvd = 0.0
    for r in rows[:200]:
        px = float(r.get('px', 0) or 0)
        sz = float(r.get('sz', 0) or 0)
        side = str(r.get('side', r.get('dir', ''))).lower()
        notional = px * sz if px and sz else float(r.get('notional', 0) or 0)
        if 'buy' in side or side in ('b', 'bid'):
            cvd += notional
        elif 'sell' in side or side in ('s', 'ask'):
            cvd -= notional
    denom = max(abs(cvd), 1.0)
    return float(np.clip(cvd / denom, -1, 1) * 0.7)


def _signal_liq_clusters(conn, price: float) -> float:
    rows = get_latest_heatmap(conn, near_price=price, limit=6)
    if not rows:
        return 0.0
    up = down = 0.0
    for r in rows:
        mid = (float(r['price_low']) + float(r['price_high'])) / 2.0
        dist = abs(mid - price) / max(price, 1e-9)
        if dist > 0.01:
            continue
        if mid > price:
            up += float(r.get('short_liq_usd', 0))
        if mid < price:
            down += float(r.get('long_liq_usd', 0))
    if up == down:
        return 0.0
    return 0.5 if up > down else -0.5


def _signals(conn, df: pd.DataFrame, regime: RegimeState) -> dict[str, float]:
    price = float(df['close'].iloc[-1])
    return {
        'trend': _signal_trend(df),
        'range_context': _signal_range_context(df),
        'volume': _signal_volume(df),
        'volatility_state': _signal_volatility(df, regime.atr_regime, regime.bb_squeeze),
        'sr_proximity': _signal_sr(conn, price),
        'momentum': _signal_momentum(df),
        'weekly_pattern': _signal_weekly_pattern(int(df['open_time'].iloc[-1] // 1000)),
        'funding_oi': _signal_funding_oi(conn),
        'cvd': _signal_cvd(),
        'liq_clusters': _signal_liq_clusters(conn, price),
    }


def _score_probs(signal_vals: dict[str, float], weights: dict[str, float], weekday: int) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    su = sd = ss = 0.0
    breakdown = {}
    for k, s in signal_vals.items():
        w = float(weights.get(k, 0))
        up = max(0.0, s)
        dn = max(0.0, -s)
        sw = max(0.0, 1.0 - abs(s))
        su += w * up
        sd += w * dn
        ss += w * sw
        breakdown[k] = {'signal': float(s), 'weight': w, 'up': w * up, 'down': w * dn, 'sideways': w * sw}
    # Framework preferred directional window includes Monday and Tuesday.
    if weekday in (0, 1):
        su, sd = su * 1.15, sd * 1.15
    if weekday in (5, 6):
        ss = ss * 1.2
    total = max(su + sd + ss, 1e-9)
    probs = {'up': su / total, 'down': sd / total, 'sideways': ss / total}
    return probs, breakdown


def _blend(child: dict[str, float], parent: dict[str, float], alpha: float) -> dict[str, float]:
    out = {k: child[k] * (1 - alpha) + parent[k] * alpha for k in ('up', 'down', 'sideways')}
    t = sum(out.values())
    return {k: v / t for k, v in out.items()}


def _confidence_from_regime(regime_conf: float, probs: dict[str, float]) -> float:
    top = max(probs.values())
    return float(np.clip(0.4 * regime_conf + 0.6 * top, 0.0, 1.0))


def _commentary(timeframe: str, regime: RegimeState, probs: dict[str, float], breakdown: dict[str, dict[str, float]]) -> str:
    dom = max(probs, key=probs.get)
    support = sorted(breakdown.items(), key=lambda kv: kv[1][dom], reverse=True)[:2]
    oppose = sorted(breakdown.items(), key=lambda kv: kv[1][dom])[0]
    s1 = f"Bitcoin is currently in a {regime.regime} regime on the {timeframe} timeframe (ADX {regime.adx:.0f}, Hurst {regime.hurst:.2f})."
    s2 = f"Probability distribution: Sideways {probs['sideways']:.0%} | Up {probs['up']:.0%} | Down {probs['down']:.0%}."
    s3 = f"Supporting factors: {support[0][0]} and {support[1][0]} are currently contributing most to {dom}."
    s4 = f"Primary risk: {oppose[0]} is pulling against this view."
    s5 = "Current market structure favours this distribution if key support/resistance levels continue to hold."
    return " ".join([s1, s2, s3, s4, s5])


def _current_brier_penalty(conn, timeframe: str) -> float:
    r = conn.execute("SELECT brier_score FROM model_calibration_metrics WHERE timeframe=? ORDER BY eval_date DESC LIMIT 1", (timeframe,)).fetchone()
    if not r or r[0] is None:
        return 0.0
    b = float(r[0])
    if b <= 0.25:
        return 0.0
    return float(np.clip((b - 0.20) * 5.0, 0.0, 1.0))


def _apply_humility(probs: dict[str, float], blend: float) -> dict[str, float]:
    if blend <= 0:
        return probs
    u = 1.0 / 3.0
    out = {k: probs[k] * (1 - blend) + u * blend for k in probs}
    t = sum(out.values())
    return {k: v / t for k, v in out.items()}


def compute_probability_snapshot(conn, cfg: dict | None = None, timeframe: str = 'all') -> dict:
    cfg = cfg or load_config()
    v = (cfg.get('data') or {}).get('primary_venue', 'binance_perp')
    d = (cfg.get('data') or {}).get('derivatives_venue', 'hyperliquid_perp')

    fetch_history(conn, 'BTCUSDT', v, '4h', days=14)
    fetch_history(conn, 'BTCUSDT', v, '1d', days=400)
    fetch_history(conn, 'BTCUSDT', v, '1w', days=1200)
    fetch_funding(conn, venue=d)
    fetch_oi(conn, venue=d)

    tf_list = TIMEFRAMES if timeframe == 'all' else (timeframe,)
    now = int(time.time())
    raw_probs, states, breakdowns = {}, {}, {}

    for tf in tf_list:
        df = _latest_df(conn, tf, v)
        if len(df) < 60:
            continue
        atrs = _atr(df)
        atr_pct = float((atrs.iloc[-1] / df['close'].iloc[-1]) if pd.notna(atrs.iloc[-1]) else 0.0)
        atr_roll = (atrs / df['close']).rolling(30).mean().iloc[-1]
        atr_roll = float(atr_roll if pd.notna(atr_roll) else atr_pct)
        if atr_pct < 0.5 * max(atr_roll, 1e-9):
            atr_reg = 'low'
        elif atr_pct > 1.5 * max(atr_roll, 1e-9):
            atr_reg = 'high'
        else:
            atr_reg = 'normal'
        adx = _adx(df)
        hurst = _hurst(df['close'])
        bbw, squeeze = _bb_width_pct(df['close'])
        sms = _sma_slope(df['close'], 50)
        regime_name, r_conf = _classify_regime(adx, hurst, atr_reg, squeeze, sms)
        state = RegimeState(tf, regime_name, adx, hurst, atr_pct, atr_reg, bbw, squeeze, r_conf)
        states[tf] = state
        conn.execute(
            "INSERT INTO market_regime_snapshots(snapshot_time,timeframe,regime,adx,hurst,atr_pct,atr_regime,bb_width_pct,bb_squeeze,confidence) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (now, tf, state.regime, state.adx, state.hurst, state.atr_pct, state.atr_regime, state.bb_width_pct, state.bb_squeeze, state.confidence),
        )
        regime_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        sig = _signals(conn, df, state)
        weights = WEIGHTS[_regime_weight_key(state.regime)]
        weekday = time.gmtime(now).tm_wday
        probs, bd = _score_probs(sig, weights, weekday)
        blend = _current_brier_penalty(conn, tf)
        probs = _apply_humility(probs, blend)
        conf = _confidence_from_regime(state.confidence, probs)
        breakdowns[tf] = bd
        raw_probs[tf] = {**probs, 'confidence': conf, 'weights': weights, 'regime_id': regime_id, 'signal_vals': sig}

    if '1w' in raw_probs and '1d' in raw_probs:
        p = _blend({k: raw_probs['1d'][k] for k in ('up','down','sideways')}, {k: raw_probs['1w'][k] for k in ('up','down','sideways')}, 0.15)
        raw_probs['1d'].update(p)
    if '1d' in raw_probs and '4h' in raw_probs:
        p = _blend({k: raw_probs['4h'][k] for k in ('up','down','sideways')}, {k: raw_probs['1d'][k] for k in ('up','down','sideways')}, 0.10)
        p['sideways'] = min(1.0, p['sideways'] + 0.04)
        t = p['up'] + p['down'] + p['sideways']
        raw_probs['4h'].update({k: p[k]/t for k in ('up','down','sideways')})

    if '1w' in raw_probs:
        p = {k: raw_probs['1w'][k] for k in ('up','down','sideways')}
        p['sideways'] = max(0.0, p['sideways'] - 0.03)
        p['up'] += 0.015; p['down'] += 0.015
        t = sum(p.values())
        raw_probs['1w'].update({k: p[k]/t for k in ('up','down','sideways')})

    out = {}
    for tf, vals in raw_probs.items():
        probs = {k: vals[k] for k in ('up','down','sideways')}
        regime = states[tf]
        commentary = _commentary(tf, regime, probs, breakdowns[tf])
        conn.execute(
            """
            INSERT INTO direction_probability_snapshots(
                snapshot_time,timeframe,regime_id,prob_up,prob_down,prob_sideways,
                raw_score_up,raw_score_down,raw_score_sideways,signal_breakdown,weights_used,
                commentary,confidence_score
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                now, tf, vals['regime_id'], probs['up'], probs['down'], probs['sideways'],
                probs['up'], probs['down'], probs['sideways'], json.dumps(breakdowns[tf]), json.dumps(vals['weights']),
                commentary, vals['confidence'],
            ),
        )
        out[tf] = {
            'regime': regime.regime,
            'adx': regime.adx,
            'hurst': regime.hurst,
            'atr_pct': regime.atr_pct,
            'bb_width_pct': regime.bb_width_pct,
            'prob_up': probs['up'],
            'prob_down': probs['down'],
            'prob_sideways': probs['sideways'],
            'confidence': vals['confidence'],
            'commentary': commentary,
        }
    conn.commit()
    return {'ok': True, 'timeframes': out, 'snapshot_time': now}


def score_probability_outcomes(conn) -> dict:
    now = int(time.time())
    rows = conn.execute(
        "SELECT id,timeframe,snapshot_time,prob_up,prob_down,prob_sideways,signal_breakdown FROM direction_probability_snapshots WHERE outcome IS NULL ORDER BY snapshot_time ASC"
    ).fetchall()
    scored = 0
    for r in rows:
        rid, tf, ts, pu, pdn, ps, sb = r
        if now - int(ts) < HORIZON_SEC.get(tf, 0):
            continue
        s_ms = int(ts * 1000)
        e_ms = int((ts + HORIZON_SEC[tf]) * 1000)
        p0 = conn.execute("SELECT close FROM candles WHERE symbol='BTCUSDT' AND timeframe=? AND open_time>=? ORDER BY open_time ASC LIMIT 1", (tf, s_ms)).fetchone()
        p1 = conn.execute("SELECT close FROM candles WHERE symbol='BTCUSDT' AND timeframe=? AND open_time>=? ORDER BY open_time ASC LIMIT 1", (tf, e_ms)).fetchone()
        if not p0 or not p1:
            continue
        p0, p1 = float(p0[0]), float(p1[0])
        ch = (p1 - p0) / max(p0, 1e-9)
        th = MOVE_THRESH[tf]
        outcome = 'up' if ch > th else ('down' if ch < -th else 'sideways')
        y = {'up': 1.0 if outcome == 'up' else 0.0, 'down': 1.0 if outcome == 'down' else 0.0, 'sideways': 1.0 if outcome == 'sideways' else 0.0}
        brier = (pu - y['up'])**2 + (pdn - y['down'])**2 + (ps - y['sideways'])**2
        prob_actual = max(1e-9, pu if outcome == 'up' else (pdn if outcome == 'down' else ps))
        ll = -math.log(prob_actual)
        conn.execute("UPDATE direction_probability_snapshots SET outcome=?,outcome_time=?,outcome_pct_change=?,brier_score=?,log_loss=? WHERE id=?", (outcome, now, ch, brier, ll, rid))

        try:
            b = json.loads(sb or '{}')
        except Exception:
            b = {}
        wd = time.gmtime(ts).tm_wday
        for name, v in b.items():
            s = float((v or {}).get('signal', 0))
            pointed = ('up' if s > 0.05 else ('down' if s < -0.05 else 'sideways'))
            corr = 1 if pointed == outcome else 0
            conn.execute(
                """
                INSERT INTO signal_accuracy_history(signal_name,timeframe,regime,day_of_week,correct_count,total_count,accuracy_rate,contribution_correctness,last_updated)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(signal_name,timeframe,regime,day_of_week)
                DO UPDATE SET
                  correct_count=correct_count+excluded.correct_count,
                  total_count=total_count+excluded.total_count,
                  accuracy_rate=(correct_count+excluded.correct_count)*1.0/(total_count+excluded.total_count),
                  contribution_correctness=(correct_count+excluded.correct_count)*1.0/(total_count+excluded.total_count),
                  last_updated=excluded.last_updated
                """,
                (name, tf, None, wd, corr, 1, corr, corr, now),
            )
        scored += 1

    for tf in TIMEFRAMES:
        vals = conn.execute("SELECT prob_up,prob_down,prob_sideways,outcome,brier_score,log_loss FROM direction_probability_snapshots WHERE timeframe=? AND outcome IS NOT NULL AND snapshot_time>=?", (tf, now - 90*24*3600)).fetchall()
        if len(vals) < 10:
            continue
        briers = [float(x[4]) for x in vals if x[4] is not None]
        lls = [float(x[5]) for x in vals if x[5] is not None]
        acc50 = []
        for pu, pdn, ps, out, *_ in vals:
            top = max([('up',pu),('down',pdn),('sideways',ps)], key=lambda z: z[1])
            if top[1] >= 0.5:
                acc50.append(1 if top[0] == out else 0)
        conn.execute(
            "INSERT INTO model_calibration_metrics(eval_date,timeframe,sample_size,brier_score,log_loss,accuracy_at_50pct_threshold,accuracy_at_60pct_threshold,accuracy_at_70pct_threshold,reliability_curve,calibration_intercept,calibration_slope) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (now, tf, len(vals), float(np.mean(briers)), float(np.mean(lls)), float(np.mean(acc50)) if acc50 else None, None, None, json.dumps({}), None, None),
        )
    conn.commit()
    return {'ok': True, 'scored': scored}


def get_probability_score(conn, timeframe: str = 'all') -> dict:
    tfs = TIMEFRAMES if timeframe == 'all' else (timeframe,)
    out = {}
    for tf in tfs:
        r = conn.execute(
            "SELECT snapshot_time,prob_up,prob_down,prob_sideways,confidence_score,commentary FROM direction_probability_snapshots WHERE timeframe=? ORDER BY snapshot_time DESC LIMIT 1",
            (tf,),
        ).fetchone()
        c = conn.execute("SELECT brier_score FROM model_calibration_metrics WHERE timeframe=? ORDER BY eval_date DESC LIMIT 1", (tf,)).fetchone()
        if r:
            out[tf] = {
                'snapshot_time': int(r[0]), 'prob_up': float(r[1]), 'prob_down': float(r[2]), 'prob_sideways': float(r[3]),
                'confidence': float(r[4]) if r[4] is not None else None, 'commentary': r[5], 'brier': (float(c[0]) if c and c[0] is not None else None)
            }
    return {'ok': True, 'timeframes': out}


def get_probability_history(conn, timeframe: str, limit: int = 20):
    rows = conn.execute(
        "SELECT snapshot_time,prob_up,prob_down,prob_sideways,outcome,outcome_pct_change,brier_score,log_loss FROM direction_probability_snapshots WHERE timeframe=? ORDER BY snapshot_time DESC LIMIT ?",
        (timeframe, int(limit)),
    ).fetchall()
    return [
        {'snapshot_time': int(r[0]), 'prob_up': float(r[1]), 'prob_down': float(r[2]), 'prob_sideways': float(r[3]), 'outcome': r[4], 'outcome_pct_change': r[5], 'brier_score': r[6], 'log_loss': r[7]}
        for r in rows
    ]


def get_regime_state(conn, timeframe: str = 'all'):
    tfs = TIMEFRAMES if timeframe == 'all' else (timeframe,)
    out = {}
    for tf in tfs:
        r = conn.execute("SELECT snapshot_time,regime,adx,hurst,atr_pct,atr_regime,bb_width_pct,bb_squeeze,confidence FROM market_regime_snapshots WHERE timeframe=? ORDER BY snapshot_time DESC LIMIT 1", (tf,)).fetchone()
        if r:
            out[tf] = {'snapshot_time': r[0], 'regime': r[1], 'adx': r[2], 'hurst': r[3], 'atr_pct': r[4], 'atr_regime': r[5], 'bb_width_pct': r[6], 'bb_squeeze': r[7], 'confidence': r[8]}
    return {'ok': True, 'timeframes': out}


def explain_probability(conn, timeframe: str = '4h'):
    r = conn.execute("SELECT snapshot_time,signal_breakdown,weights_used,commentary FROM direction_probability_snapshots WHERE timeframe=? ORDER BY snapshot_time DESC LIMIT 1", (timeframe,)).fetchone()
    if not r:
        return {'ok': False, 'reason': 'no_snapshot'}
    return {'ok': True, 'snapshot_time': r[0], 'signal_breakdown': json.loads(r[1] or '{}'), 'weights_used': json.loads(r[2] or '{}'), 'commentary': r[3]}


def calibration_report(conn):
    out = {}
    for tf in TIMEFRAMES:
        r = conn.execute("SELECT eval_date,sample_size,brier_score,log_loss,accuracy_at_50pct_threshold,accuracy_at_60pct_threshold,accuracy_at_70pct_threshold,reliability_curve FROM model_calibration_metrics WHERE timeframe=? ORDER BY eval_date DESC LIMIT 1", (tf,)).fetchone()
        if r:
            out[tf] = {
                'eval_date': r[0], 'sample_size': r[1], 'brier_score': r[2], 'log_loss': r[3],
                'accuracy_at_50pct_threshold': r[4], 'accuracy_at_60pct_threshold': r[5], 'accuracy_at_70pct_threshold': r[6],
                'reliability_curve': json.loads(r[7] or '{}')
            }
    return {'ok': True, 'timeframes': out}


def signal_accuracy(conn, signal_name: str | None = None):
    if signal_name:
        rows = conn.execute("SELECT signal_name,timeframe,regime,day_of_week,correct_count,total_count,accuracy_rate,last_updated FROM signal_accuracy_history WHERE signal_name=? ORDER BY accuracy_rate DESC", (signal_name,)).fetchall()
    else:
        rows = conn.execute("SELECT signal_name,timeframe,regime,day_of_week,correct_count,total_count,accuracy_rate,last_updated FROM signal_accuracy_history ORDER BY accuracy_rate DESC LIMIT 200").fetchall()
    return [
        {'signal_name': r[0], 'timeframe': r[1], 'regime': r[2], 'day_of_week': r[3], 'correct_count': r[4], 'total_count': r[5], 'accuracy_rate': r[6], 'last_updated': r[7]}
        for r in rows
    ]


def kelly_size(conn, account_balance: float, max_risk_pct: float = 2.0):
    score = get_probability_score(conn, timeframe='4h')['timeframes'].get('4h')
    if not score:
        return {'ok': False, 'reason': 'no_4h_probability'}
    cal = calibration_report(conn)['timeframes'].get('4h')
    if not cal or cal.get('sample_size', 0) < 100 or (cal.get('brier_score') or 1) > 0.30:
        return {'ok': False, 'reason': 'insufficient_or_uncalibrated_history'}
    p = max(score['prob_up'], score['prob_down'])
    b = 1.5
    full = ((p * (b + 1)) - 1) / b
    frac = max(0.0, 0.25 * full)
    cap = min(0.10, max_risk_pct / 100.0)
    pct = min(cap, frac)
    return {'ok': True, 'kelly_fraction': full, 'fractional_kelly': frac, 'position_pct': pct, 'position_size': float(account_balance) * pct}
