from __future__ import annotations

import sqlite3

from btc_analyst.config import load_config
from btc_analyst.hermes import tools
from btc_analyst.notify.log_sink import log_message


def heartbeat():
    s = tools.sanity_check()
    s['ok'] = bool(s.get('bars_fresh', False))
    return s


def on_4h_close():
    try:
        zr = tools.force_zone_recompute()
        sr = tools.run_setups_cycle()
        pr = tools.run_probability_cycle('4h')
        return {'zone_recompute': zr, 'setups_cycle': sr, 'probability_cycle': pr}
    except Exception as e:
        tools.record_pipeline_failure('schedule_on_4h_close', e)
        return {'ok': False, 'error': str(e)}


def on_daily_close():
    try:
        zr = tools.force_zone_recompute()
        pr = tools.run_probability_cycle('all')
        return {'zone_recompute': zr, 'probability_cycle': pr}
    except Exception as e:
        tools.record_pipeline_failure('schedule_on_daily_close', e)
        return {'ok': False, 'error': str(e)}


def run_daily_report():
    try:
        return tools.generate_report('today', force=True)
    except Exception as e:
        tools.record_pipeline_failure('schedule_run_daily_report', e)
        return {'ok': False, 'error': str(e)}


def run_weekly_review():
    try:
        setups = tools.get_setups('closed')
        pr = tools.run_probability_cycle('all')
        retro = tools.run_probability_retrospective()
        cals = tools.calibration_report_tool()
        conn = sqlite3.connect('./data/btc_analyst.db')
        buckets = {
            '0_25': conn.execute("SELECT COUNT(*), COALESCE(AVG(hit),0) FROM bot_calls WHERE realized_at IS NOT NULL AND conviction BETWEEN 0 AND 25").fetchone(),
            '26_50': conn.execute("SELECT COUNT(*), COALESCE(AVG(hit),0) FROM bot_calls WHERE realized_at IS NOT NULL AND conviction BETWEEN 26 AND 50").fetchone(),
            '51_75': conn.execute("SELECT COUNT(*), COALESCE(AVG(hit),0) FROM bot_calls WHERE realized_at IS NOT NULL AND conviction BETWEEN 51 AND 75").fetchone(),
            '76_100': conn.execute("SELECT COUNT(*), COALESCE(AVG(hit),0) FROM bot_calls WHERE realized_at IS NOT NULL AND conviction BETWEEN 76 AND 100").fetchone(),
        }
        med = conn.execute("SELECT COALESCE(AVG(realized_r_multiple),0) FROM (SELECT realized_r_multiple FROM bot_calls WHERE realized_at IS NOT NULL ORDER BY realized_r_multiple LIMIT 2 - (SELECT COUNT(*) FROM bot_calls WHERE realized_at IS NOT NULL) % 2 OFFSET (SELECT (COUNT(*) - 1) / 2 FROM bot_calls WHERE realized_at IS NOT NULL))").fetchone()[0]
        conn.close()
        bucket_fmt = {k: {'count': int(v[0]), 'hit_rate': round(float(v[1]) * 100.0, 2)} for k, v in buckets.items()}
        return {
            'ok': True,
            'closed_setups': len(setups),
            'probability_cycle': pr,
            'probability_retro': retro,
            'calibration': cals,
            'call_hit_rate_by_conviction_bucket': bucket_fmt,
            'median_r_multiple_per_realized_call': round(float(med or 0), 4),
        }
    except Exception as e:
        tools.record_pipeline_failure('schedule_run_weekly_review', e)
        return {'ok': False, 'error': str(e)}


def cme_close_warning():
    log_message('CME close approaching: prefer stronger confluence >=85 for fresh entries.')
    return {'ok': True}


def cme_open_check():
    return {'ok': True, 'note': 'CME open check executed'}


def db_maintenance():
    conn = sqlite3.connect('./data/btc_analyst.db')
    conn.execute('VACUUM')
    conn.execute('ANALYZE')
    conn.close()
    return {'ok': True}


def apply_decay():
    conn = sqlite3.connect('./data/btc_analyst.db')
    conn.execute(
        "UPDATE zones SET score=score*0.99,last_updated=strftime('%s','now') WHERE status='active' AND tier IN ('weak','noise')"
    )
    conn.commit()
    conn.close()
    return {'ok': True}


def refresh_crowd_positioning():
    try:
        return tools.refresh_crowd_positioning_snapshot()
    except Exception as e:
        tools.record_pipeline_failure('schedule_refresh_crowd_positioning', e)
        return {'ok': False, 'error': str(e)}


def market_monitoring_cycle():
    try:
        mr = tools.run_market_monitoring_cycle()
        pr = tools.run_probability_cycle('4h')
        mr['probability'] = pr
        return mr
    except Exception as e:
        tools.record_pipeline_failure('schedule_market_monitoring_cycle', e)
        return {'ok': False, 'error': str(e)}


def refresh_liq_heatmap_cycle():
    try:
        cfg = load_config()
        mcfg = (cfg.get('monitoring') or {})
        bucket_size = int(mcfg.get('heatmap_bucket_size', 250))
        top_n_addresses = int(mcfg.get('heatmap_top_n_addresses', 40))
        return tools.refresh_liq_heatmap(bucket_size, top_n_addresses)
    except Exception as e:
        tools.record_pipeline_failure('schedule_refresh_liq_heatmap_cycle', e)
        return {'ok': False, 'error': str(e)}


def probability_retrospective_daily():
    try:
        return tools.run_probability_retrospective()
    except Exception as e:
        tools.record_pipeline_failure('schedule_probability_retrospective_daily', e)
        return {'ok': False, 'error': str(e)}


def probability_hourly_1d():
    try:
        return tools.run_probability_cycle('1d')
    except Exception as e:
        tools.record_pipeline_failure('schedule_probability_hourly_1d', e)
        return {'ok': False, 'error': str(e)}


def bot_call_realization_hourly():
    try:
        return tools.realize_bot_calls()
    except Exception as e:
        tools.record_pipeline_failure('schedule_bot_call_realization_hourly', e)
        return {'ok': False, 'error': str(e)}


def probability_weekly_recompute():
    try:
        out = tools.run_probability_cycle('all')
        out['retrospective'] = tools.run_probability_retrospective()
        return out
    except Exception as e:
        tools.record_pipeline_failure('schedule_probability_weekly_recompute', e)
        return {'ok': False, 'error': str(e)}
