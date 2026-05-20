from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from btc_analyst.config import load_config
from btc_analyst.analysis import run_market_monitor_cycle
from btc_analyst.analysis.heatmap import refresh_hyperliquid_heatmap, get_latest_heatmap
from btc_analyst.analysis.probability import (
    compute_probability_snapshot,
    score_probability_outcomes,
    get_probability_score,
    get_probability_history,
    get_regime_state,
    explain_probability,
    calibration_report,
    signal_accuracy,
    kelly_size,
)
from btc_analyst.reports.daily import build_report_data, render_markdown, render_telegram_digest, save_report
from btc_analyst.reports.chart import generate_charts
from btc_analyst.scoring.scorer import score_zone
from btc_analyst.sentiment.aggregator import get_latest_crowd_positioning, refresh_crowd_positioning
from btc_analyst.alerts.engine import run_alert_engine
from btc_analyst.setups.engine import run_setup_engine
from btc_analyst.storage.db import get_conn, run_migrations
from btc_analyst.context.sessions import active_sessions

DB = './data/btc_analyst.db'


def _conn():
    c = get_conn(DB)
    run_migrations(c)
    return c


def _current_bias(c):
    d = build_report_data('today', conn=c)
    return d.get('bias', 'Uncertain')


def get_state():
    c = _conn()
    row = c.execute(
        "SELECT close FROM candles WHERE symbol='BTCUSDT' AND venue='bybit_perp' AND timeframe='4h' ORDER BY open_time DESC LIMIT 1"
    ).fetchone()
    price = float(row[0]) if row else None
    zones = get_zones('strong', 'all', 5)
    pending = get_setups('active', None)
    return {
        'price': price,
        'bias': _current_bias(c),
        'active_strong_zones': zones,
        'pending_setups': pending,
        'active_sessions': active_sessions(datetime.now(timezone.utc)),
    }


def get_zones(tier='all', type='all', limit=50):
    c = _conn()
    q = "SELECT id,price_low,price_high,zone_type,source,timeframe,score,tier,status FROM zones WHERE status='active'"
    p = []
    if tier != 'all':
        q += ' AND tier=?'
        p.append(tier)
    if type != 'all':
        q += ' AND zone_type=?'
        p.append(type)
    q += ' ORDER BY score DESC LIMIT ?'
    p.append(limit)
    cols = ['id', 'price_low', 'price_high', 'zone_type', 'source', 'timeframe', 'score', 'tier', 'status']
    return [dict(zip(cols, r)) for r in c.execute(q, p).fetchall()]


def generate_report(date_str=None, force=False):
    c = _conn()
    d = date.today().isoformat() if (not date_str or date_str == 'today') else date_str
    if not force:
        row = c.execute('SELECT report_date FROM reports WHERE report_date=?', (d,)).fetchone()
        if row:
            return {'date': d, 'path': f'./reports/{d}.md', 'cached': True}
    data = build_report_data(d, conn=c)
    charts = generate_charts(c, d)
    data['charts'] = charts
    md = render_markdown(data)
    path = save_report(c, d, md, chart_paths=charts)
    return {'date': d, 'path': path, 'digest': render_telegram_digest(data), 'charts': charts}


def get_report(date):
    c = _conn()
    r = c.execute('SELECT markdown_body FROM reports WHERE report_date=?', (date,)).fetchone()
    return {'date': date, 'markdown': (r[0] if r else None)}


def list_alerts(status='all', since=None):
    c = _conn()
    q = 'SELECT id,zone_id,alert_type,created_at,triggered_at,delivery_status,condition_json FROM alerts WHERE 1=1'
    p = []
    if status == 'active':
        q += ' AND triggered_at IS NULL'
    elif status == 'fired':
        q += ' AND triggered_at IS NOT NULL'
    if since:
        ts = int(datetime.fromisoformat(since).replace(tzinfo=timezone.utc).timestamp())
        q += ' AND created_at>=?'
        p.append(ts)
    q += ' ORDER BY id DESC LIMIT 100'
    cols = ['id', 'zone_id', 'alert_type', 'created_at', 'triggered_at', 'delivery_status', 'condition_json']
    out = []
    for r in c.execute(q, p).fetchall():
        d = dict(zip(cols, r))
        d['condition'] = json.loads(d.pop('condition_json') or '{}')
        out.append(d)
    return out


def create_manual_alert(price, direction, note=''):
    c = _conn()
    key = f'manual:{direction}:{int(price)}:{int(time.time() // 3600)}'
    c.execute(
        'INSERT OR IGNORE INTO alerts(created_at,zone_id,alert_type,condition_json,delivery_status,dedupe_key) VALUES (?,?,?,?,?,?)',
        (int(time.time()), None, 'manual_price', json.dumps({'price': price, 'direction': direction, 'note': note}), 'pending', key),
    )
    c.commit()
    return {'ok': True, 'price': price, 'direction': direction, 'note': note}


def cancel_alert(id):
    c = _conn()
    c.execute(
        'UPDATE alerts SET triggered_at=?,delivery_status=? WHERE id=? AND triggered_at IS NULL',
        (int(time.time()), 'cancelled', id),
    )
    c.commit()
    return {'ok': True, 'id': id}


def get_setups(status='all', since=None):
    c = _conn()
    q = 'SELECT id,zone_id,direction,entry_price,stop_price,target1_price,target2_price,rr_to_t1,confidence,status,created_at,COALESCE(tier,\'legacy\'),COALESCE(risk_multiplier,1.0) FROM setups WHERE 1=1'
    p = []
    if status != 'all':
        q += ' AND status=?'
        p.append(status)
    if since:
        ts = int(datetime.fromisoformat(since).replace(tzinfo=timezone.utc).timestamp())
        q += ' AND created_at>=?'
        p.append(ts)
    q += ' ORDER BY id DESC LIMIT 100'
    cols = ['id', 'zone_id', 'direction', 'entry_price', 'stop_price', 'target1_price', 'target2_price', 'rr_to_t1', 'confidence', 'status', 'created_at', 'tier', 'risk_multiplier']
    return [dict(zip(cols, r)) for r in c.execute(q, p).fetchall()]


def log_call(direction, conviction, evidence=None, predicted_horizon_h=4, source='chat'):
    c = _conn()
    row = c.execute(
        "SELECT close FROM candles WHERE symbol='BTCUSDT' AND timeframe='4h' ORDER BY open_time DESC LIMIT 1"
    ).fetchone()
    price = float(row[0]) if row else None
    c.execute(
        """
        INSERT INTO bot_calls(ts,source,direction,conviction,price_at_call,evidence_json,predicted_horizon_h)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            int(time.time()),
            str(source),
            str(direction),
            int(conviction),
            price,
            json.dumps(evidence or {}),
            int(predicted_horizon_h),
        ),
    )
    c.commit()
    return {'ok': True, 'logged': 1, 'source': source, 'direction': direction, 'conviction': int(conviction), 'price_at_call': price}


def realize_bot_calls(limit=200):
    c = _conn()
    now = int(time.time())
    rows = c.execute(
        """
        SELECT id,ts,direction,price_at_call,predicted_horizon_h
        FROM bot_calls
        WHERE realized_at IS NULL
        ORDER BY ts ASC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    realized = 0
    for rid, ts, direction, p0, horizon_h in rows:
        horizon = int(horizon_h or 4) * 3600
        if int(ts) > now - horizon:
            continue
        row = c.execute(
            "SELECT close FROM candles WHERE symbol='BTCUSDT' AND timeframe='1h' AND open_time>=? ORDER BY open_time ASC LIMIT 1",
            (int((ts + horizon) * 1000),),
        ).fetchone()
        if not row or p0 in (None, 0):
            continue
        p1 = float(row[0])
        ret = (p1 - float(p0)) / float(p0)
        dirn = str(direction or 'sideways')
        if dirn == 'up':
            hit = 1 if ret > 0 else 0
            r_mult = ret / 0.01
        elif dirn == 'down':
            hit = 1 if ret < 0 else 0
            r_mult = (-ret) / 0.01
        else:
            hit = 1 if abs(ret) <= 0.0025 else 0
            r_mult = 1.0 - (abs(ret) / 0.01)
        c.execute(
            "UPDATE bot_calls SET actual_close_price=?,realized_at=?,hit=?,realized_r_multiple=? WHERE id=?",
            (p1, now, int(hit), float(r_mult), int(rid)),
        )
        realized += 1
    c.commit()
    return {'ok': True, 'realized': realized}


def run_backtest(period_start, period_end, config_overrides=None):
    if pd is None:
        return {'ok': False, 'reason': 'pandas_not_installed'}
    from backtest.harness import run_walk_forward
    c = _conn()
    start_ms = int(pd.Timestamp(period_start, tz='UTC').timestamp() * 1000)
    end_ms = int(pd.Timestamp(period_end, tz='UTC').timestamp() * 1000)
    df = pd.read_sql_query(
        "SELECT open_time,open,high,low,close,volume FROM candles WHERE symbol='BTCUSDT' AND venue='bybit_perp' AND timeframe='4h' AND open_time BETWEEN ? AND ? ORDER BY open_time",
        c,
        params=[start_ms, end_ms],
    )
    result = run_walk_forward(df)
    return {'ok': True, **result}


def force_zone_recompute():
    if pd is None:
        return {'ok': False, 'reason': 'pandas_not_installed'}
    from btc_analyst.scoring.regime import classify_regime
    from btc_analyst.zones.horizontal import detect_horizontal_zones
    from btc_analyst.zones.registry import upsert_zones
    from btc_analyst.zones.volume_zones import zones_from_profile
    from btc_analyst.zones.cme_gap import detect_cme_gaps
    c = _conn()
    cfg = load_config()
    v = (cfg.get('data') or {}).get('primary_venue', 'binance_perp')
    df4h = pd.read_sql_query(
        "SELECT open_time,open,high,low,close,volume FROM candles WHERE symbol='BTCUSDT' AND venue=? AND timeframe='4h' ORDER BY open_time",
        c,
        params=[v],
    )
    dfd = pd.read_sql_query(
        "SELECT open_time,open,high,low,close,volume FROM candles WHERE symbol='BTCUSDT' AND venue=? AND timeframe='1d' ORDER BY open_time",
        c,
        params=[v],
    )
    if df4h.empty:
        return {'ok': False, 'reason': 'no_4h_data'}
    zs = detect_horizontal_zones(df4h) + zones_from_profile(df4h, timeframe='4h') + detect_cme_gaps(df4h, timeframe='4h')
    close = df4h['close'].astype(float)
    ma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else float(close.iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else ma20
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = float((100 - (100 / (1 + rs))).iloc[-1]) if len(close) >= 20 else 50.0
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_hist = float((ema12 - ema26 - (ema12 - ema26).ewm(span=9, adjust=False).mean()).iloc[-1]) if len(close) >= 35 else 0.0
    funding_row = c.execute(
        "SELECT funding_rate FROM funding WHERE symbol='BTCUSDT' ORDER BY funding_time DESC LIMIT 1"
    ).fetchone()
    oi_rows = c.execute(
        "SELECT oi FROM open_interest WHERE symbol='BTCUSDT' ORDER BY ts DESC LIMIT 2"
    ).fetchall()
    funding = float(funding_row[0]) if funding_row and funding_row[0] is not None else 0.0
    oi_strength = 0.0
    if len(oi_rows) == 2 and oi_rows[1][0]:
        oi_ch = (float(oi_rows[0][0]) - float(oi_rows[1][0])) / float(oi_rows[1][0])
        oi_strength = min(1.0, abs(oi_ch) * 25.0)
    liq_rows = get_latest_heatmap(c, near_price=float(df4h['close'].iloc[-1]), limit=20)
    if liq_rows:
        for z in zs:
            mid = (float(z.price_low) + float(z.price_high)) / 2.0
            best = min(liq_rows, key=lambda r: abs(((r['price_low'] + r['price_high']) / 2.0) - mid))
            total = float(best.get('long_liq_usd', 0)) + float(best.get('short_liq_usd', 0))
            strength = min(1.0, total / 5_000_000.0)
            z.factors = {**(z.factors or {}), 'liquidation_cluster_strength': strength}
    regime = classify_regime(dfd if not dfd.empty else df4h)
    now_utc = pd.Timestamp.now(tz='UTC')
    ms = {'regime': regime, 'is_weekend': now_utc.weekday() >= 5, 'weekday': int(now_utc.weekday())}
    px = float(close.iloc[-1])
    trend_dir = 'bull' if ma20 >= ma50 else 'bear'
    for z in zs:
        f = z.factors or {}
        mid = (float(z.price_low) + float(z.price_high)) / 2.0
        near_ma = min(abs(mid - ma20), abs(mid - ma50)) / max(px, 1.0)
        ma_strength = max(0.0, 1.0 - (near_ma / 0.01))
        with_trend = (z.zone_type == 'support' and trend_dir == 'bull') or (z.zone_type == 'resistance' and trend_dir == 'bear')
        structure_align = 1.0 if with_trend else 0.45
        rsi_strength = min(1.0, abs(rsi - 50.0) / 20.0)
        macd_strength = min(1.0, abs(macd_hist) / max(px * 0.0015, 1.0))
        funding_strength = min(1.0, abs(funding) / 0.0005)
        f.update(
            {
                'ma_strength': ma_strength,
                'structure_align': structure_align,
                'rsi_strength': rsi_strength,
                'macd_strength': macd_strength,
                'funding_strength': funding_strength,
                'oi_strength': oi_strength,
                'range_edge': abs(mid - px) / max(px, 1.0) > 0.003,
            }
        )
        z.factors = f
    zs = [score_zone(z, cfg, ms) for z in zs]
    upsert_zones(c, zs)
    return {'ok': True, 'zones': len(zs)}


def sanity_check():
    c = _conn()
    now = int(time.time() * 1000)
    cfg = load_config()
    v = (cfg.get('data') or {}).get('primary_venue', 'binance_perp')
    last = c.execute(
        "SELECT open_time FROM candles WHERE symbol='BTCUSDT' AND venue=? AND timeframe='4h' ORDER BY open_time DESC LIMIT 1",
        (v,),
    ).fetchone()
    bars_fresh = bool(last and (now - int(last[0]) < 8 * 3600 * 1000))
    last_report = c.execute('SELECT generated_at FROM reports ORDER BY generated_at DESC LIMIT 1').fetchone()
    last_age = None if not last_report else int(time.time()) - int(last_report[0])
    pending = c.execute('SELECT COUNT(*) FROM alerts WHERE triggered_at IS NULL').fetchone()[0]
    errors = c.execute("SELECT COUNT(*) FROM bot_log WHERE level='ERROR' AND ts>=?", (int(time.time()) - 3600,)).fetchone()[0]
    health = system_health_status()
    return {
        'bars_fresh': bars_fresh,
        'ws_connected': False,
        'last_report_age': last_age,
        'pending_alerts': pending,
        'errors_last_hour': errors,
        'health_status': health.get('health_status'),
        'stale_components': health.get('stale_components', []),
    }


def refresh_crowd_positioning_snapshot():
    c = _conn()
    cfg = load_config()
    return refresh_crowd_positioning(c, cfg)


def get_crowd_positioning():
    c = _conn()
    row = get_latest_crowd_positioning(c)
    return row or {'ok': False, 'reason': 'no_snapshot'}


def _log_pipeline(component: str, message: str, context: dict | None = None):
    c = _conn()
    c.execute(
        "INSERT INTO bot_log(ts,level,component,message,context_json) VALUES (?,?,?,?,?)",
        (int(time.time()), 'INFO', component, message, json.dumps(context or {})),
    )
    c.commit()


def _emit_internal_alert(c, alert_type: str, payload: dict, dedupe_key: str):
    c.execute(
        'INSERT OR IGNORE INTO alerts(created_at,zone_id,alert_type,condition_json,delivery_status,dedupe_key) VALUES (?,?,?,?,?,?)',
        (int(time.time()), None, alert_type, json.dumps(payload), 'pending', dedupe_key),
    )
    c.commit()


def record_pipeline_failure(component: str, err: Exception | str, context: dict | None = None, dedupe_scope: str = 'hour'):
    c = _conn()
    msg = str(err)
    err_type = type(err).__name__ if isinstance(err, Exception) else 'RuntimeError'
    ts = int(time.time())
    slot = ts // 3600 if dedupe_scope == 'hour' else ts // 86400
    dedupe_key = f"{component}:{err_type}:{msg[:120]}:{slot}"
    c.execute(
        'INSERT OR IGNORE INTO pipeline_failures(ts,component,error_type,error_message,context_json,dedupe_key,status) VALUES (?,?,?,?,?,?,?)',
        (ts, component, err_type, msg[:1000], json.dumps(context or {}), dedupe_key, 'open'),
    )
    c.execute(
        "INSERT INTO bot_log(ts,level,component,message,context_json) VALUES (?,?,?,?,?)",
        (ts, 'ERROR', component, msg[:1000], json.dumps(context or {})),
    )
    recent_count = c.execute(
        'SELECT COUNT(*) FROM pipeline_failures WHERE component=? AND ts>=?',
        (component, ts - 3600),
    ).fetchone()[0]
    if recent_count >= 3:
        payload = {
            'report_short': f"{component} failures x{recent_count} in 1h",
            'component': component,
            'error_type': err_type,
            'error_message': msg[:240],
            'recent_count_1h': int(recent_count),
        }
        _emit_internal_alert(c, 'pipeline_failure', payload, f"pipeline_failure:{component}:{slot}")
    c.commit()
    return {'ok': True, 'component': component, 'recent_count_1h': int(recent_count)}


def system_health_status():
    c = _conn()
    now = int(time.time())
    cfg = load_config()
    mcfg = (cfg.get('monitoring') or {})
    pulse_max_age = int(mcfg.get('stale_pulse_seconds', 1800))
    crowd_max_age = int(mcfg.get('stale_crowd_seconds', 21600))
    prob_max_age = int(mcfg.get('stale_probability_seconds', 21600))

    checks = {
        'pulse': ('SELECT ts FROM market_pulse_snapshots ORDER BY ts DESC LIMIT 1', pulse_max_age),
        'crowd': ('SELECT ts FROM crowd_positioning_snapshots ORDER BY ts DESC LIMIT 1', crowd_max_age),
        'probability_4h': ("SELECT snapshot_time FROM direction_probability_snapshots WHERE timeframe='4h' ORDER BY snapshot_time DESC LIMIT 1", prob_max_age),
    }
    stale_components = []
    ages = {}
    for name, (q, max_age) in checks.items():
        row = c.execute(q).fetchone()
        age = None if (not row or row[0] is None) else now - int(row[0])
        ages[name] = age
        if age is None or age > max_age:
            stale_components.append(name)

    errors_1h = c.execute("SELECT COUNT(*) FROM bot_log WHERE level='ERROR' AND ts>=?", (now - 3600,)).fetchone()[0]
    health = 'healthy' if (not stale_components and int(errors_1h) == 0) else 'degraded'
    return {
        'health_status': health,
        'stale_components': stale_components,
        'ages_seconds': ages,
        'errors_last_hour': int(errors_1h),
    }


def run_market_monitoring_cycle():
    c = _conn()
    cfg = load_config()
    try:
        out = run_market_monitor_cycle(c, cfg)
    except Exception as e:
        record_pipeline_failure('market_monitoring_cycle', e, {'stage': 'run_market_monitor_cycle'})
        return {'ok': False, 'reason': 'exception', 'error': str(e)}
    if out.get('ok'):
        try:
            price = float((out.get('snapshot') or {}).get('price'))
            zones = get_zones('all', 'all', 200)
            fired = run_alert_engine(c, zones, price)
            out['internal_alerts_fired'] = len(fired)
        except Exception as e:
            out['internal_alerts_error'] = str(e)
            record_pipeline_failure('market_monitoring_cycle', e, {'stage': 'run_alert_engine'})
    health = system_health_status()
    out['health'] = health
    if health['stale_components']:
        slot = int(time.time()) // 1800
        _emit_internal_alert(
            c,
            'staleness_warning',
            {
                'report_short': f"stale components: {', '.join(health['stale_components'])}",
                'stale_components': health['stale_components'],
                'ages_seconds': health['ages_seconds'],
            },
            f"staleness_warning:{slot}:{','.join(sorted(health['stale_components']))}",
        )
    _log_pipeline('market_monitoring_cycle', 'cycle_completed', out)
    return out


def run_setups_cycle():
    c = _conn()
    cfg = load_config()
    out = run_setup_engine(c, cfg)
    _log_pipeline('setups_cycle', 'setups_evaluated', out)
    return out


def explain_setup_blockers():
    c = _conn()
    row = c.execute("SELECT id,score,tier,zone_type,price_low,price_high FROM zones WHERE status='active' ORDER BY score DESC LIMIT 1").fetchone()
    top = None
    if row:
        top = {
            'id': row[0], 'score': row[1], 'tier': row[2], 'zone_type': row[3],
            'price_low': row[4], 'price_high': row[5],
        }
    setup_rows = c.execute("SELECT COUNT(*) FROM setups").fetchone()[0]
    return {'top_zone': top, 'setups_count': setup_rows}


def refresh_liq_heatmap(bucket_size=250, top_n_addresses=200):
    c = _conn()
    out = refresh_hyperliquid_heatmap(c, bucket_size=int(bucket_size), top_n_addresses=int(top_n_addresses))
    _log_pipeline('liq_heatmap_cycle', 'heatmap_refreshed', out)
    return out


def get_liq_heatmap(limit=10):
    c = _conn()
    r = c.execute("SELECT close FROM candles WHERE symbol='BTCUSDT' AND timeframe='4h' ORDER BY open_time DESC LIMIT 1").fetchone()
    near = float(r[0]) if r else None
    return {'near_price': near, 'rows': get_latest_heatmap(c, near_price=near, limit=int(limit))}


def get_liq_clusters(n=5):
    c = _conn()
    return {'clusters': get_latest_heatmap(c, near_price=None, limit=int(n))}


def liq_pressure_at_price(price):
    c = _conn()
    rows = get_latest_heatmap(c, near_price=float(price), limit=5)
    pressure = sum((x.get('net_liq_usd') or 0) for x in rows)
    return {'price': float(price), 'estimated_net_liq_pressure': pressure, 'nearby_buckets': rows}


def run_probability_cycle(timeframe='all'):
    c = _conn()
    cfg = load_config()
    out = compute_probability_snapshot(c, cfg, timeframe=timeframe)
    _log_pipeline('probability_cycle', 'probabilities_updated', out)
    return out


def run_probability_retrospective():
    c = _conn()
    out = score_probability_outcomes(c)
    _log_pipeline('probability_retrospective', 'outcomes_scored', out)
    return out


def get_probability(timeframe='all'):
    c = _conn()
    return get_probability_score(c, timeframe=timeframe)


def get_probability_history_tool(timeframe='4h', limit=20):
    c = _conn()
    return {'timeframe': timeframe, 'rows': get_probability_history(c, timeframe=timeframe, limit=int(limit))}


def explain_probability_tool(timeframe='4h'):
    c = _conn()
    return explain_probability(c, timeframe=timeframe)


def regime_state(timeframe='all'):
    c = _conn()
    return get_regime_state(c, timeframe=timeframe)


def calibration_report_tool():
    c = _conn()
    return calibration_report(c)


def signal_accuracy_tool(signal_name=None):
    c = _conn()
    return {'rows': signal_accuracy(c, signal_name=signal_name)}


def kelly_size_tool(account_balance, max_risk_pct=2.0):
    c = _conn()
    return kelly_size(c, account_balance=float(account_balance), max_risk_pct=float(max_risk_pct))
