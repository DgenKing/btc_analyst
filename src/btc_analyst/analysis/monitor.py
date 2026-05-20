from __future__ import annotations

import json
import time

import pandas as pd

from btc_analyst.config import load_config
from btc_analyst.data.funding_store import fetch_funding
from btc_analyst.data.ohlcv_store import fetch_history
from btc_analyst.data.oi_store import fetch_oi
from btc_analyst.sentiment.aggregator import _latest_bybit_funding_and_oi


def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(alpha=1 / length, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / length, adjust=False).mean()
    rs = ma_up / ma_down.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _latest_1h_df(conn, venue: str) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT open_time, open, high, low, close, volume
        FROM candles
        WHERE symbol='BTCUSDT' AND venue=? AND timeframe='1h'
        ORDER BY open_time DESC
        LIMIT 300
        """,
        conn,
        params=[venue],
    ).sort_values("open_time")


def _calc_candle_shape(last_row: pd.Series) -> dict:
    o = float(last_row["open"])
    h = float(last_row["high"])
    l = float(last_row["low"])
    c = float(last_row["close"])
    rng = max(h - l, 1e-9)
    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    close_pos = ((c - l) / rng) * 100.0
    return {
        "candle_body_pct_1h": (body / rng) * 100.0,
        "upper_wick_pct_1h": (upper_wick / rng) * 100.0,
        "lower_wick_pct_1h": (lower_wick / rng) * 100.0,
        "close_position_pct_1h": close_pos,
    }


def _score_direction(latest: dict) -> tuple[float, str, str, dict]:
    score = 0.0
    comp = {}

    rsi_v = latest.get("rsi_1h")
    if rsi_v is not None:
        rsi_score = max(-1.0, min(1.0, (float(rsi_v) - 50.0) / 10.0))
        score += rsi_score
        comp["rsi"] = rsi_score

    macd_hist = latest.get("macd_hist_1h")
    if macd_hist is not None:
        mh = float(macd_hist)
        mh_score = 0.8 if mh > 0 else (-0.8 if mh < 0 else 0.0)
        score += mh_score
        comp["macd_hist_sign"] = mh_score

    macd_slope = latest.get("macd_hist_slope_1h")
    if macd_slope is not None:
        ms = float(macd_slope)
        ms_score = 0.7 if ms > 0 else (-0.7 if ms < 0 else 0.0)
        score += ms_score
        comp["macd_hist_slope"] = ms_score

    oi_delta = latest.get("oi_delta_24h_pct")
    funding = latest.get("funding_8h")
    if oi_delta is not None and funding is not None:
        # OI rising + positive funding => long participation; falling + negative => short pressure.
        if float(oi_delta) > 0 and float(funding) >= 0:
            score += 0.6
            comp["oi_funding_alignment"] = 0.6
        elif float(oi_delta) < 0 and float(funding) <= 0:
            score -= 0.6
            comp["oi_funding_alignment"] = -0.6
        else:
            comp["oi_funding_alignment"] = 0.0

    close_pos = latest.get("close_position_pct_1h")
    if close_pos is not None:
        cp = float(close_pos)
        cp_score = 0.4 if cp >= 60 else (-0.4 if cp <= 40 else 0.0)
        score += cp_score
        comp["close_position"] = cp_score

    if score >= 1.6:
        return score, "up_bias", "high", comp
    if score >= 0.5:
        return score, "up_bias", "medium", comp
    if score <= -1.6:
        return score, "down_bias", "high", comp
    if score <= -0.5:
        return score, "down_bias", "medium", comp
    return score, "neutral", "low", comp


def run_market_monitor_cycle(conn, cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()

    data_cfg = (cfg.get('data') or {})
    primary_venue = data_cfg.get('primary_venue', 'binance_perp')
    deriv_venue = data_cfg.get('derivatives_venue', primary_venue)

    # Keep 1h/4h bars + derivatives current.
    fetch_history(conn, "BTCUSDT", primary_venue, "1h", days=3)
    fetch_history(conn, "BTCUSDT", primary_venue, "4h", days=7)
    fetch_funding(conn, venue=deriv_venue)
    fetch_oi(conn, venue=deriv_venue)

    df = _latest_1h_df(conn, primary_venue)
    if len(df) < 40:
        return {"ok": False, "reason": "insufficient_1h_bars"}

    rsi_series = _rsi(df["close"], length=(cfg.get("indicators", {}).get("rsi_length", 14)))
    macd_line, macd_signal, macd_hist = _macd(df["close"], *cfg.get("indicators", {}).get("macd", [12, 26, 9]))

    last = df.iloc[-1]
    shape = _calc_candle_shape(last)

    funding_8h, oi_delta = _latest_bybit_funding_and_oi(conn, venue=deriv_venue)
    hist_vals = macd_hist.dropna()
    hist_now = float(hist_vals.iloc[-1]) if not hist_vals.empty else None
    hist_prev = float(hist_vals.iloc[-2]) if len(hist_vals) >= 2 else None
    hist_slope = (hist_now - hist_prev) if (hist_now is not None and hist_prev is not None) else None

    snap = {
        "ts": int(time.time()),
        "price": float(last["close"]),
        "rsi_1h": float(rsi_series.iloc[-1]) if not rsi_series.empty and pd.notna(rsi_series.iloc[-1]) else None,
        "macd_1h": float(macd_line.iloc[-1]) if pd.notna(macd_line.iloc[-1]) else None,
        "macd_signal_1h": float(macd_signal.iloc[-1]) if pd.notna(macd_signal.iloc[-1]) else None,
        "macd_hist_1h": hist_now,
        "macd_hist_slope_1h": hist_slope,
        "oi_delta_24h_pct": oi_delta,
        "funding_8h": funding_8h,
        **shape,
    }

    score, label, confidence, comps = _score_direction(snap)
    snap["momentum_score"] = score
    snap["direction_label"] = label
    snap["confidence"] = confidence
    snap["components_json"] = json.dumps(comps)

    conn.execute(
        """
        INSERT OR REPLACE INTO market_pulse_snapshots(
            ts, price, rsi_1h, macd_1h, macd_signal_1h, macd_hist_1h, macd_hist_slope_1h,
            oi_delta_24h_pct, funding_8h, candle_body_pct_1h, upper_wick_pct_1h,
            lower_wick_pct_1h, close_position_pct_1h, momentum_score, direction_label,
            confidence, components_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            snap["ts"], snap["price"], snap["rsi_1h"], snap["macd_1h"], snap["macd_signal_1h"],
            snap["macd_hist_1h"], snap["macd_hist_slope_1h"], snap["oi_delta_24h_pct"], snap["funding_8h"],
            snap["candle_body_pct_1h"], snap["upper_wick_pct_1h"], snap["lower_wick_pct_1h"],
            snap["close_position_pct_1h"], snap["momentum_score"], snap["direction_label"],
            snap["confidence"], snap["components_json"],
        ),
    )
    conn.commit()

    return {"ok": True, "snapshot": snap}
