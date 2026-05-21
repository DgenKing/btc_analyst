from __future__ import annotations

import time
import json

from .dedupe import dedupe_key, is_duplicate_within
from .persistence import save_alert


def _latest_market_state(conn):
    try:
        pulse = conn.execute(
            "SELECT ts, price, rsi_1h, macd_hist_1h, direction_label, confidence FROM market_pulse_snapshots ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    except Exception:
        pulse = None
    try:
        prob = conn.execute(
            "SELECT prob_up, prob_down, prob_sideways, confidence_score FROM direction_probability_snapshots WHERE timeframe='4h' ORDER BY snapshot_time DESC LIMIT 1"
        ).fetchone()
    except Exception:
        prob = None
    try:
        regime = conn.execute(
            "SELECT regime FROM market_regime_snapshots WHERE timeframe='4h' ORDER BY snapshot_time DESC LIMIT 1"
        ).fetchone()
    except Exception:
        regime = None

    return {
        'pulse_ts': int(pulse[0]) if pulse and pulse[0] is not None else None,
        'price': float(pulse[1]) if pulse and pulse[1] is not None else None,
        'rsi_1h': float(pulse[2]) if pulse and pulse[2] is not None else None,
        'macd_hist_1h': float(pulse[3]) if pulse and pulse[3] is not None else None,
        'direction_label': str(pulse[4]) if pulse and pulse[4] is not None else 'unknown',
        'confidence': str(pulse[5]) if pulse and pulse[5] is not None else 'unknown',
        'prob_up_4h': float(prob[0]) if prob and prob[0] is not None else None,
        'prob_down_4h': float(prob[1]) if prob and prob[1] is not None else None,
        'prob_sideways_4h': float(prob[2]) if prob and prob[2] is not None else None,
        'prob_conf_4h': float(prob[3]) if prob and prob[3] is not None else None,
        'regime_4h': str(regime[0]) if regime and regime[0] is not None else 'unknown',
    }


def _build_alert_report(zone: dict, price: float, state: dict) -> dict:
    zmid = (float(zone['price_low']) + float(zone['price_high'])) / 2.0
    distance_pct = abs(float(price) - zmid) / max(float(price), 1e-9) * 100.0
    report_short = (
        f"Zone entry alert: price ${price:,.0f} inside zone #{zone['id']} "
        f"(${zone['price_low']:,.0f}-${zone['price_high']:,.0f}). "
        f"4h={state.get('direction_label','unknown')} ({state.get('confidence','unknown')}), "
        f"regime={state.get('regime_4h','unknown')}, "
        f"p(side/up/down)={int((state.get('prob_sideways_4h') or 0)*100)}/"
        f"{int((state.get('prob_up_4h') or 0)*100)}/"
        f"{int((state.get('prob_down_4h') or 0)*100)}%."
    )
    return {
        'decision': 'zone_entry',
        'why': 'price entered monitored zone',
        'current_price': float(price),
        'zone_id': int(zone['id']),
        'zone_low': float(zone['price_low']),
        'zone_high': float(zone['price_high']),
        'zone_tier': str(zone.get('tier', 'unknown')),
        'zone_score': float(zone.get('score', 0.0)),
        'distance_to_zone_mid_pct': round(distance_pct, 3),
        'market_state': {
            'direction_1h': state.get('direction_label'),
            'confidence_1h': state.get('confidence'),
            'regime_4h': state.get('regime_4h'),
            'prob_sideways_4h': state.get('prob_sideways_4h'),
            'prob_up_4h': state.get('prob_up_4h'),
            'prob_down_4h': state.get('prob_down_4h'),
            'prob_conf_4h': state.get('prob_conf_4h'),
        },
        'report_short': report_short,
        'created_at': int(time.time()),
    }


def _emit_alert(conn, zone_id: int | None, alert_type: str, payload: dict, key: str, fired: list):
    save_alert(conn, zone_id, alert_type, payload, key)
    try:
        conn.execute(
            "INSERT INTO bot_log(ts,level,component,message,context_json) VALUES (?,?,?,?,?)",
            (int(time.time()), 'INFO', 'alert_engine', 'alert_generated', json.dumps(payload)),
        )
        conn.commit()
    except Exception:
        pass
    fired.append({'zone_id': zone_id, 'type': alert_type, 'report_short': payload.get('report_short')})


def _build_weak_knife_signal(support_zone: dict, price: float, state: dict) -> dict:
    low = float(support_zone['price_low'])
    hi = float(support_zone['price_high'])
    rsi = state.get('rsi_1h')
    breakdown_pct = ((low - price) / max(low, 1e-9)) * 100.0
    rsi_txt = f"{rsi:.1f}" if rsi is not None else 'n/a'
    report_short = (
        f"Weak knife-catch watch: ${price:,.0f} is {breakdown_pct:.2f}% below support #{support_zone['id']} "
        f"(${low:,.0f}-${hi:,.0f}), RSI1h={rsi_txt}, "
        f"regime={state.get('regime_4h','unknown')}. Watch only; confirmation required."
    )
    return {
        'decision': 'weak_knife_catch_watch',
        'why': 'support breakdown + oversold context; early reversal watch only',
        'current_price': float(price),
        'zone_id': int(support_zone['id']),
        'zone_low': low,
        'zone_high': hi,
        'zone_tier': str(support_zone.get('tier', 'unknown')),
        'zone_score': float(support_zone.get('score', 0.0)),
        'breakdown_below_support_pct': round(breakdown_pct, 3),
        'market_state': {
            'direction_1h': state.get('direction_label'),
            'confidence_1h': state.get('confidence'),
            'rsi_1h': state.get('rsi_1h'),
            'macd_hist_1h': state.get('macd_hist_1h'),
            'regime_4h': state.get('regime_4h'),
            'prob_sideways_4h': state.get('prob_sideways_4h'),
            'prob_up_4h': state.get('prob_up_4h'),
            'prob_down_4h': state.get('prob_down_4h'),
        },
        'strength': 'weak',
        'non_actionable': True,
        'report_short': report_short,
        'created_at': int(time.time()),
    }


def _should_emit_knife_alert(conn, zone_id: int, price: float, min_move_pct: float = 0.5, lookback_hours: int = 48) -> bool:
    """Suppress repeated knife alerts unless price moved far enough from last knife alert price."""
    since_ts = int(time.time()) - (lookback_hours * 3600)
    rows = conn.execute(
        "SELECT condition_json FROM alerts WHERE alert_type='weak_knife_catch_watch' AND zone_id=? AND created_at>=? ORDER BY id DESC LIMIT 20",
        (zone_id, since_ts),
    ).fetchall()
    for (condition_json,) in rows:
        try:
            c = json.loads(condition_json or '{}')
            p0 = c.get('current_price')
            if p0 is None:
                continue
            p0 = float(p0)
            if p0 <= 0:
                continue
            move_pct = abs(float(price) - p0) / p0 * 100.0
            if move_pct < min_move_pct:
                return False
        except Exception:
            continue
    return True


def run_alert_engine(conn, zones, price, cfg=None):
    fired = []
    state = _latest_market_state(conn)
    dedupe_window_minutes = int((((cfg or {}).get('alerts') or {}).get('dedupe_window_minutes', 60)))
    dedupe_window_seconds = max(60, dedupe_window_minutes * 60)

    for z in zones:
        if z['price_low'] <= price <= z['price_high']:
            if is_duplicate_within(conn, 'zone_entry', int(z['id']), dedupe_window_seconds):
                continue
            k = dedupe_key('zone_entry', z['id'], int(time.time() // dedupe_window_seconds))
            payload = _build_alert_report(z, float(price), state)
            _emit_alert(conn, z['id'], 'zone_entry', payload, k, fired)

    # Weak knife-catch signal (diagnostic only):
    # if price breaks just below nearest support and RSI is oversold, emit watch signal.
    support_zones = [z for z in zones if str(z.get('zone_type', '')).lower() == 'support']
    if support_zones and state.get('rsi_1h') is not None:
        # choose the nearest support that is currently above price (recently broken)
        broken_candidates = [z for z in support_zones if float(price) < float(z['price_low'])]
        if broken_candidates:
            nearest = sorted(broken_candidates, key=lambda z: float(z['price_low']) - float(price))[0]
        else:
            nearest = sorted(
                support_zones,
                key=lambda z: abs(float(price) - ((float(z['price_low']) + float(z['price_high'])) / 2.0)),
            )[0]
        low = float(nearest['price_low'])
        breakdown_pct = ((low - float(price)) / max(low, 1e-9)) * 100.0
        is_oversold = float(state['rsi_1h']) <= 35.0
        is_shallow_break = 0.0 < breakdown_pct <= 0.8
        if is_oversold and is_shallow_break:
            zone_id = int(nearest['id'])
            knife_time_dedupe = not is_duplicate_within(conn, 'weak_knife_catch_watch', zone_id, 30 * 60)
            if knife_time_dedupe and _should_emit_knife_alert(conn, zone_id, float(price), min_move_pct=0.5, lookback_hours=48):
                k = dedupe_key('weak_knife_catch_watch', zone_id, int(time.time() // 1800))
                payload = _build_weak_knife_signal(nearest, float(price), state)
                _emit_alert(conn, zone_id, 'weak_knife_catch_watch', payload, k, fired)

    return fired
