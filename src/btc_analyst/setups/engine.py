from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from btc_analyst.setups.builder import build_setup, persist_setup
from btc_analyst.setups.filters import apply_hard_filters
from btc_analyst.setups.reactions import detect_reactions
from btc_analyst.setups.triggers import detect_trigger
from btc_analyst.analysis.probability import get_probability_score, get_regime_state
from btc_analyst.context.sessions import active_sessions
from btc_analyst.indicators.structure import trend_label

RISK_UNIT_PCT = 1.0


def _trend_from_df(df: pd.DataFrame, timeframe: str) -> str:
    lbl = trend_label(df, timeframe)
    if lbl == 'up':
        return 'bull'
    if lbl == 'down':
        return 'bear'
    return 'neutral'


def _weekly_timing_quality(now_utc: datetime) -> tuple[str, float]:
    wd = now_utc.weekday()  # Mon=0 ... Sun=6
    # Sunday preferred window starts when futures/liquidity return (~22:00 UTC).
    if wd == 6:
        if int(now_utc.hour) >= 22:
            return ('optimal_window', 1.0)
        return ('midweek_window', 0.8)
    if wd in (0, 1):
        return ('optimal_window', 1.0)
    if wd in (2, 3):
        return ('midweek_window', 0.8)
    return ('late_week_window', 0.6)


def _weekend_impulse_context(conn, venue: str, symbol: str, now_utc: datetime, lookback_weeks: int = 104, q_low: float = 0.25, q_high: float = 0.75) -> dict:
    dfd = pd.read_sql_query(
        """
        SELECT open_time, high, low
        FROM candles
        WHERE symbol=? AND venue=? AND timeframe='1d'
        ORDER BY open_time
        """,
        conn,
        params=[symbol, venue],
    )
    if dfd.empty:
        return {'ok': False, 'reason': 'no_daily_candles'}

    ot = pd.to_numeric(dfd['open_time'], errors='coerce')
    unit = 'ms' if float(ot.dropna().iloc[-1]) > 10_000_000_000 else 's'
    dfd['dt'] = pd.to_datetime(ot, unit=unit, utc=True)
    dfd['date'] = dfd['dt'].dt.date
    dfd['weekday'] = dfd['dt'].dt.weekday
    dfd['iso_year'] = dfd['dt'].dt.isocalendar().year.astype(int)
    dfd['iso_week'] = dfd['dt'].dt.isocalendar().week.astype(int)

    weekends = []
    for (_, _), g in dfd.groupby(['iso_year', 'iso_week']):
        sat = g[g['weekday'] == 5]
        sun = g[g['weekday'] == 6]
        if sat.empty or sun.empty:
            continue
        sat_row = sat.iloc[0]
        sun_row = sun.iloc[0]
        lo = min(float(sat_row['low']), float(sun_row['low']))
        hi = max(float(sat_row['high']), float(sun_row['high']))
        if lo <= 0:
            continue
        weekends.append(
            {
                'sunday_date': sun_row['date'],
                'weekend_range_pct': ((hi / lo) - 1.0) * 100.0,
            }
        )

    if not weekends:
        return {'ok': False, 'reason': 'no_complete_weekends'}

    wdf = pd.DataFrame(weekends).sort_values('sunday_date')
    latest_sunday = now_utc.date()
    while latest_sunday.weekday() != 6:
        latest_sunday = (pd.Timestamp(latest_sunday) - pd.Timedelta(days=1)).date()

    eligible = wdf[wdf['sunday_date'] <= latest_sunday]
    if eligible.empty:
        return {'ok': False, 'reason': 'no_eligible_weekend'}

    current = eligible.iloc[-1]
    hist = eligible.tail(max(int(lookback_weeks), 12))
    ql = float(hist['weekend_range_pct'].quantile(q_low))
    qh = float(hist['weekend_range_pct'].quantile(q_high))
    val = float(current['weekend_range_pct'])
    bucket = 'mid'
    if val <= ql:
        bucket = 'low'
    elif val >= qh:
        bucket = 'high'
    return {
        'ok': True,
        'bucket': bucket,
        'weekend_range_pct': round(val, 3),
        'quantile_low_pct': round(ql, 3),
        'quantile_high_pct': round(qh, 3),
        'lookback_weeks': int(len(hist)),
        'reference_sunday': str(current['sunday_date']),
    }


def _latest_4h(conn, venue: str, symbol: str):
    df = pd.read_sql_query(
        """
        SELECT open_time, open, high, low, close, volume
        FROM candles
        WHERE symbol=? AND venue=? AND timeframe='4h'
        ORDER BY open_time DESC
        LIMIT 2
        """,
        conn,
        params=[symbol, venue],
    ).sort_values("open_time")
    if df.empty:
        return None, None
    cur = df.iloc[-1].to_dict()
    prev = df.iloc[-2].to_dict() if len(df) >= 2 else None
    return cur, prev


def _atr_daily_pct(conn, venue: str, symbol: str):
    dfd = pd.read_sql_query(
        """
        SELECT open_time, high, low, close
        FROM candles
        WHERE symbol=? AND venue=? AND timeframe='1d'
        ORDER BY open_time DESC
        LIMIT 30
        """,
        conn,
        params=[symbol, venue],
    ).sort_values("open_time")
    if dfd.empty or len(dfd) < 14:
        return None
    atr = float((dfd["high"] - dfd["low"]).rolling(14).mean().iloc[-1])
    last = float(dfd["close"].iloc[-1])
    return (atr / last) * 100.0 if last else None


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _latest_4h_indicators(conn, venue: str, symbol: str) -> tuple[float | None, float | None]:
    d = pd.read_sql_query(
        "SELECT close FROM candles WHERE symbol=? AND venue=? AND timeframe='4h' ORDER BY open_time DESC LIMIT 120",
        conn,
        params=[symbol, venue],
    )
    if d.empty or len(d) < 35:
        return None, None
    close = d['close'].astype(float).iloc[::-1].reset_index(drop=True)

    # RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = (100 - (100 / (1 + rs))).iloc[-1]

    # MACD hist (12,26,9)
    macd = _ema(close, 12) - _ema(close, 26)
    signal = _ema(macd, 9)
    hist = (macd - signal).iloc[-1]

    rsi_val = float(rsi) if pd.notna(rsi) else None
    hist_val = float(hist) if pd.notna(hist) else None
    return rsi_val, hist_val


def _asia_us_reversal_signal(conn, venue: str, symbol: str, now_utc: datetime, pump_dump_threshold_pct: float = 0.6) -> dict:
    sessions = active_sessions(now_utc)
    in_tokyo = 'tokyo' in sessions
    # We only apply this as a hard trigger around early Asia flow (00:00-04:00 UTC)
    if not in_tokyo or now_utc.hour > 4:
        return {'active': False, 'reason': 'outside_asia_reversal_window'}

    d = pd.read_sql_query(
        "SELECT open_time, close FROM candles WHERE symbol=? AND venue=? AND timeframe='1h' ORDER BY open_time DESC LIMIT 12",
        conn,
        params=[symbol, venue],
    )
    if d.empty or len(d) < 8:
        return {'active': False, 'reason': 'insufficient_1h_candles'}
    d = d.sort_values('open_time').reset_index(drop=True)
    closes = d['close'].astype(float).tolist()
    us_move_pct = ((closes[-1] / closes[-7]) - 1.0) * 100.0

    if abs(us_move_pct) < float(pump_dump_threshold_pct):
        return {
            'active': False,
            'reason': 'us_move_below_threshold',
            'us_move_pct': round(float(us_move_pct), 3),
            'threshold_pct': float(pump_dump_threshold_pct),
        }

    expected_direction = 'short' if us_move_pct > 0 else 'long'
    pattern = 'us_pump_asia_dump' if us_move_pct > 0 else 'us_dump_asia_pump'
    return {
        'active': True,
        'pattern': pattern,
        'us_move_pct': round(float(us_move_pct), 3),
        'threshold_pct': float(pump_dump_threshold_pct),
        'expected_direction': expected_direction,
    }


def _mtf_alignment(conn, direction: str, venue: str, symbol: str) -> tuple[bool, str, float, dict]:
    dfd = pd.read_sql_query(
        "SELECT open_time,high,low,close FROM candles WHERE symbol=? AND venue=? AND timeframe='1d' ORDER BY open_time",
        conn,
        params=[symbol, venue],
    )
    df12 = pd.read_sql_query(
        "SELECT open_time,high,low,close FROM candles WHERE symbol=? AND venue=? AND timeframe='12h' ORDER BY open_time",
        conn,
        params=[symbol, venue],
    )
    df8 = pd.read_sql_query(
        "SELECT open_time,high,low,close FROM candles WHERE symbol=? AND venue=? AND timeframe='8h' ORDER BY open_time",
        conn,
        params=[symbol, venue],
    )
    df4 = pd.read_sql_query(
        "SELECT open_time,high,low,close FROM candles WHERE symbol=? AND venue=? AND timeframe='4h' ORDER BY open_time",
        conn,
        params=[symbol, venue],
    )

    daily = _trend_from_df(dfd, '1d')
    h12 = _trend_from_df(df12, '12h')
    h8 = _trend_from_df(df8, '8h')
    h4 = _trend_from_df(df4, '4h')

    expected = 'bull' if direction == 'long' else 'bear'
    snap = {'daily': daily, 'h12': h12, 'h8': h8, 'h4': h4}

    if daily == 'neutral':
        if h12 == expected and h8 == expected:
            if h4 not in (expected, 'neutral'):
                return False, '4h_conflict', 0.0, snap
            return True, 'htf_neutral_with_ltf_align', 0.8, snap
        return False, 'daily_neutral_no_ltf_align', 0.0, snap

    if daily != expected:
        return False, 'daily_conflict', 0.0, snap

    mid_conflict = (h12 not in (expected, 'neutral')) and (h8 not in (expected, 'neutral'))
    if mid_conflict:
        return False, 'mid_tf_conflict', 0.0, snap

    mid_aligned = int(h12 == expected) + int(h8 == expected)
    if h4 != expected and h4 != 'neutral':
        return False, '4h_conflict', 0.0, snap

    if mid_aligned == 2 and h4 == expected:
        return True, 'full_alignment', 1.0, snap
    if mid_aligned >= 1:
        return True, 'partial_alignment', 0.85, snap
    return True, 'daily_only_alignment', 0.75, snap


def run_setup_engine(conn, cfg: dict) -> dict:
    venue = ((cfg.get('data') or {}).get('primary_venue', 'binance_perp'))
    symbol = str((cfg.get('data') or {}).get('symbol', 'BTCUSDT'))
    cur, prev = _latest_4h(conn, venue, symbol)
    if cur is None:
        return {"ok": False, "reason": "no_4h_candle"}

    # Probability + regime gating (direction-neutral, soft unless volatile_chop)
    pstate = get_probability_score(conn, timeframe='all').get('timeframes', {})
    rstate = get_regime_state(conn, timeframe='all').get('timeframes', {})
    up_ok = 0
    dn_ok = 0
    probability_soft_gate = False
    if pstate:
        up_ok = sum(1 for tf in ('4h', '1d', '1w') if (pstate.get(tf) or {}).get('prob_up', 0) > 0.45)
        dn_ok = sum(1 for tf in ('4h', '1d', '1w') if (pstate.get(tf) or {}).get('prob_down', 0) > 0.45)
        if max(up_ok, dn_ok) < 2:
            probability_soft_gate = True
    if any((rstate.get(tf) or {}).get('regime') == 'volatile_chop' for tf in ('4h', '1d')):
        return {"ok": True, "attempted": 0, "persisted": 0, "reasons": {"volatile_chop_gate": 1}}

    mon = (cfg.get("monitoring", {}) or {})
    min_zone_score = float(mon.get("diagnostic_min_zone_score", 40.0))
    now_utc = datetime.now(timezone.utc)
    weekend_ctx = _weekend_impulse_context(
        conn,
        venue,
        symbol,
        now_utc,
        lookback_weeks=int(mon.get('weekend_impulse_lookback_weeks', 104)),
        q_low=float(mon.get('weekend_impulse_low_quantile', 0.25)),
        q_high=float(mon.get('weekend_impulse_high_quantile', 0.75)),
    )
    asia_reversal_cfg = bool(mon.get('asia_reversal_hard_trigger_enabled', True))
    asia_reversal_threshold = float(mon.get('asia_reversal_threshold_pct', 0.6))
    asia_reversal = _asia_us_reversal_signal(conn, venue, symbol, now_utc, asia_reversal_threshold)

    zones = conn.execute(
        """
        SELECT id, price_low, price_high, zone_type, score, tier
        FROM zones
        WHERE status='active' AND score >= ?
        ORDER BY score DESC
        LIMIT 30
        """,
        (min_zone_score,),
    ).fetchall()
    fallback_used = False
    if not zones:
        zones = conn.execute(
            """
            SELECT id, price_low, price_high, zone_type, score, tier
            FROM zones
            WHERE status='active'
            ORDER BY score DESC
            LIMIT 30
            """
        ).fetchall()
        fallback_used = True

    atr_daily_pct = _atr_daily_pct(conn, venue, symbol)
    setup_cfg = (cfg.get('setups') or {})
    proximity_pct = float(setup_cfg.get('reaction_proximity_pct', 0.35))
    wick_ratio_min = float(setup_cfg.get('rejection_wick_ratio_min', 1.2))
    rsi_4h, macd_hist_4h = _latest_4h_indicators(conn, venue, symbol)
    attempted = 0
    persisted = 0
    reasons: dict[str, int] = {}
    timing_quality, timing_multiplier = _weekly_timing_quality(now_utc)
    trade_frequency_cfg = ((cfg.get('setups') or {}).get('trade_frequency') or {})
    max_qualified_setups_per_week = int(
        trade_frequency_cfg.get(
            'max_qualified_setups_per_week',
            trade_frequency_cfg.get('max_trades_per_week', 2),
        )
    )
    week_window_secs = int(trade_frequency_cfg.get('week_window_seconds', 7 * 24 * 3600))
    now_ts = int(now_utc.timestamp())
    week_cutoff_ts = now_ts - week_window_secs
    existing_weekly_qualified = int(
        conn.execute(
            """
            SELECT COUNT(1)
            FROM setups
            WHERE created_at >= ?
              AND status IN ('active', 'pending_b')
            """,
            (week_cutoff_ts,),
        ).fetchone()[0]
    )
    tier_cfg = ((cfg.get('setups') or {}).get('tiering') or {})
    tiering_enabled = bool(tier_cfg.get('enabled', True))
    a_required = int(tier_cfg.get('a_required_factors', 3))
    b_required = int(tier_cfg.get('b_required_factors', 2))
    b_unlock_bars = int(tier_cfg.get('b_unlock_after_no_a_4h_bars', 2))
    risk_mult = tier_cfg.get('risk_multiplier', {}) or {}
    risk_a = float(risk_mult.get('a', 1.0))
    risk_b = float(risk_mult.get('b', 0.5))
    risk_c = float(risk_mult.get('c', 0.0))
    cur_bar_open = int(cur.get("open_time") or 0)
    state_row = conn.execute(
        "SELECT state_value FROM setup_engine_state WHERE state_key='last_a_setup_4h_bar' LIMIT 1"
    ).fetchone()
    last_a_bar = int(state_row[0]) if (state_row and state_row[0]) else None
    a_persisted_this_cycle = False

    for z in zones:
        zone = {
            "id": z[0],
            "price_low": float(z[1]),
            "price_high": float(z[2]),
            "zone_type": z[3],
            "score": float(z[4]),
            "tier": z[5],
        }
        attempted += 1

        reaction = detect_reactions(
            cur,
            prev,
            zone,
            rsi=rsi_4h,
            macd_hist=macd_hist_4h,
            proximity_pct=proximity_pct,
            wick_ratio_min=wick_ratio_min,
        )
        if not reaction:
            reasons["no_reaction"] = reasons.get("no_reaction", 0) + 1
            continue

        trigger = detect_trigger(cur, zone, reaction)
        if not trigger:
            reasons["no_trigger"] = reasons.get("no_trigger", 0) + 1
            continue

        direction = "long" if zone["zone_type"] == "support" else "short"
        if asia_reversal_cfg and asia_reversal.get('active'):
            expected = str(asia_reversal.get('expected_direction'))
            if direction != expected:
                reasons['asia_reversal_direction_mismatch'] = reasons.get('asia_reversal_direction_mismatch', 0) + 1
                continue

        aligned, align_label, align_multiplier, tf_snapshot = _mtf_alignment(conn, direction, venue, symbol)
        if not aligned:
            reasons[align_label] = reasons.get(align_label, 0) + 1
            continue

        entry = float(cur["close"])
        stop = float(zone["price_low"] if direction == "long" else zone["price_high"])

        target_rows = conn.execute(
            """
            SELECT price_low, price_high
            FROM zones
            WHERE status='active' AND zone_type=?
            ORDER BY score DESC
            LIMIT 12
            """,
            ("resistance" if direction == "long" else "support",),
        ).fetchall()
        if not target_rows:
            reasons["no_target_zone"] = reasons.get("no_target_zone", 0) + 1
            continue

        min_rr = float((cfg.get('setups') or {}).get('min_rr_t1', 1.5))
        stop_dist = abs(entry - stop)
        if stop_dist <= 0:
            reasons["invalid_stop_distance"] = reasons.get("invalid_stop_distance", 0) + 1
            continue

        candidates = []
        for tr in target_rows:
            cand = float(tr[1] if direction == "long" else tr[0])
            rr = abs(cand - entry) / stop_dist
            candidates.append((cand, rr))

        # choose the nearest target that still satisfies min RR; fallback to best RR candidate
        viable = [x for x in candidates if x[1] >= min_rr]
        if viable:
            t1 = sorted(viable, key=lambda x: x[1])[0][0]
        else:
            t1 = sorted(candidates, key=lambda x: x[1], reverse=True)[0][0]

        # second target = next farther candidate if available
        farther = [x[0] for x in sorted(candidates, key=lambda x: x[1]) if abs(x[0] - entry) > abs(t1 - entry)]
        t2 = farther[0] if farther else None

        setup = build_setup(zone, entry, stop, t1, t2, reaction, trigger)
        effective_timing_multiplier = timing_multiplier
        if weekend_ctx.get('ok') and now_utc.weekday() == 1 and weekend_ctx.get('bucket') == 'high':
            effective_timing_multiplier *= 0.9
        if probability_soft_gate:
            effective_timing_multiplier *= 0.9
            reasons['probability_soft_gate'] = reasons.get('probability_soft_gate', 0) + 1
        setup['confidence'] = round(float(setup['confidence']) * align_multiplier * effective_timing_multiplier, 2)
        # Phase 5 A/B/C setup tiering:
        # factor_count includes structure reaction, execution trigger, and probability alignment.
        factor_count = 0
        if reaction:
            factor_count += 1
        if trigger:
            factor_count += 1
        if max(up_ok, dn_ok) >= 2:
            factor_count += 1
        if max(up_ok, dn_ok) >= 3:
            factor_count += 1

        setup_tier = 'C'
        if tiering_enabled:
            is_a = (
                factor_count >= a_required
                and str(zone.get('tier', '')).lower() == 'strong'
                and align_label in ('full_alignment', 'partial_alignment')
                and float(setup['rr_to_t1']) >= float(min_rr)
            )
            is_b = (
                factor_count >= b_required
                and align_label in ('full_alignment', 'partial_alignment', 'daily_only_alignment', 'htf_neutral_with_ltf_align')
                and float(setup['rr_to_t1']) >= float(min_rr)
            )
            if is_a:
                setup_tier = 'A'
            elif is_b:
                setup_tier = 'B'
            else:
                setup_tier = 'C'
        else:
            setup_tier = 'legacy'

        bars_since_last_a = None
        if last_a_bar is not None and cur_bar_open and cur_bar_open >= last_a_bar:
            bars_since_last_a = int((cur_bar_open - last_a_bar) // (4 * 3600 * 1000))
        b_unlocked = bool(last_a_bar is None or (bars_since_last_a is not None and bars_since_last_a >= b_unlock_bars))
        alertable = setup_tier == 'A' or (setup_tier == 'B' and b_unlocked)
        setup['status'] = 'active' if alertable else 'pending_b'
        setup['tier'] = setup_tier
        setup['risk_multiplier'] = risk_a if setup_tier == 'A' else (risk_b if setup_tier == 'B' else risk_c)
        setup['notes_json'] = json.dumps(
            {
                'setup_tier': setup_tier,
                'factor_count': factor_count,
                'b_unlocked': b_unlocked,
                'bars_since_last_a': bars_since_last_a,
                'alertable': alertable,
                'risk_multiplier': setup['risk_multiplier'],
                'timing_quality': timing_quality,
                'timing_multiplier': effective_timing_multiplier,
                'alignment_status': align_label,
                'alignment_multiplier': align_multiplier,
                'tf_snapshot': tf_snapshot,
                'generated_weekday_utc': now_utc.strftime('%A'),
                'weekend_impulse': weekend_ctx,
                'asia_reversal': asia_reversal,
                'asia_reversal_hard_trigger_enabled': asia_reversal_cfg,
                'probability_soft_gate': probability_soft_gate,
                'probability_up_count': up_ok,
                'probability_down_count': dn_ok,
            }
        )

        # anti-spam dedupe: do not persist equivalent active setup repeatedly
        dup = conn.execute(
            """
            SELECT id FROM setups
            WHERE zone_id=? AND direction=? AND reaction_type=? AND trigger_type=? AND status='active'
            ORDER BY created_at DESC LIMIT 1
            """,
            (setup['zone_id'], setup['direction'], setup['reaction_type'], setup['trigger_type']),
        ).fetchone()
        if dup:
            reasons['duplicate_active_setup'] = reasons.get('duplicate_active_setup', 0) + 1
            continue
        if setup_tier == 'C':
            reasons['tier_c_no_trade'] = reasons.get('tier_c_no_trade', 0) + 1
            continue
        ok, reason = apply_hard_filters(
            setup["rr_to_t1"],
            cfg,
            atr_daily_pct=atr_daily_pct,
            direction=setup["direction"],
            zone_score=zone["score"],
            with_weekly_trend=True,
            funding_extreme_same_direction=False,
            macro_event_window=False,
        )
        if not ok:
            reasons[reason or "hard_filter_reject"] = reasons.get(reason or "hard_filter_reject", 0) + 1
            continue

        if (existing_weekly_qualified + persisted) >= max_qualified_setups_per_week:
            reasons['trade_frequency_cap_reached'] = reasons.get('trade_frequency_cap_reached', 0) + 1
            continue

        persist_setup(conn, setup)
        persisted += 1
        if setup_tier == 'A':
            a_persisted_this_cycle = True

    if a_persisted_this_cycle and cur_bar_open:
        conn.execute(
            """
            INSERT INTO setup_engine_state(state_key, state_value, updated_at)
            VALUES ('last_a_setup_4h_bar', ?, strftime('%s','now'))
            ON CONFLICT(state_key) DO UPDATE SET
              state_value=excluded.state_value,
              updated_at=excluded.updated_at
            """,
            (str(cur_bar_open),),
        )
        conn.commit()
    return {
        "ok": True,
        "attempted": attempted,
        "persisted": persisted,
        "reasons": reasons,
        "min_zone_score": min_zone_score,
        "fallback_all_active_used": fallback_used,
        "timing_quality_current": timing_quality,
        "weekend_impulse": weekend_ctx,
        "asia_reversal": asia_reversal,
        "asia_reversal_hard_trigger_enabled": asia_reversal_cfg,
        "probability_soft_gate": probability_soft_gate,
        "probability_up_count": up_ok,
        "probability_down_count": dn_ok,
        "tiering_enabled": tiering_enabled,
        "last_a_setup_4h_bar": last_a_bar,
        "current_4h_bar_open": cur_bar_open,
    }
