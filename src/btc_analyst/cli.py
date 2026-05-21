import json

import click
import pandas as pd
from btc_analyst.storage.db import get_conn, run_migrations
from btc_analyst.config import load_config
from btc_analyst.data.ohlcv_store import fetch_history
from btc_analyst.data.funding_store import fetch_funding
from btc_analyst.data.oi_store import fetch_oi
from btc_analyst.reports.daily import build_report_data, render_markdown, save_report
from btc_analyst.reports.chart import generate_charts
from btc_analyst.scoring.regime import classify_regime
from btc_analyst.analysis import run_market_monitor_cycle
from btc_analyst.analysis.probability import (
    compute_probability_snapshot,
    score_probability_outcomes,
    get_probability_score,
    explain_probability,
    get_regime_state,
    calibration_report,
)
from btc_analyst.hermes.tools import get_state as hermes_get_state, get_probability as hermes_get_probability, regime_state as hermes_regime_state, get_crowd_positioning as hermes_get_crowd_positioning, get_setups as hermes_get_setups

DB_PATH = './data/btc_analyst.db'


@click.group()
def cli():
    pass


@cli.command('init')
def init_cmd():
    c = get_conn(DB_PATH)
    run_migrations(c)
    click.echo(f'Initialized {DB_PATH}')


@cli.command('seed')
@click.option('--days', default=1825, type=int)
def seed_cmd(days):
    c = get_conn(DB_PATH)
    cfg = load_config()
    for tf in cfg['data']['timeframes']:
        fetch_history(c, cfg['data']['symbol'], cfg['data']['primary_venue'], tf, days)
    fetch_history(c, cfg['data']['symbol'], cfg['data']['spot_venue'], '4h', days)
    fetch_history(c, cfg['data']['symbol'], cfg['data']['spot_venue'], '1d', days)
    fetch_funding(c)
    fetch_oi(c)
    click.echo('Seed complete')


@cli.command('zones')
@click.option('--tier', default='strong')
def zones_cmd(tier):
    from btc_analyst.hermes.tools import force_zone_recompute
    result = force_zone_recompute()
    if not result.get('ok'):
        click.echo(f'Recompute failed: {result}')
        return
    c = get_conn(DB_PATH)
    rows = c.execute(
        'SELECT id,price_low,price_high,zone_type,source,score,tier FROM zones WHERE status=\'active\' AND tier=? ORDER BY score DESC LIMIT 25',
        (tier,),
    ).fetchall()
    if not rows:
        click.echo(f'No active zones at tier={tier!r}. Active tiers:')
        for r in c.execute('SELECT tier, COUNT(*), MAX(score) FROM zones WHERE status=\'active\' GROUP BY tier ORDER BY MAX(score) DESC').fetchall():
            click.echo(f'  {r[0]}: {r[1]} zones, max_score={r[2]}')
    else:
        for r in rows:
            click.echo(r)


@cli.command('report')
@click.option('--date', 'date_str', default='today')
@click.option('--force', is_flag=True, default=False)
def report_cmd(date_str, force):
    c = get_conn(DB_PATH)
    cfg = load_config()
    d = build_report_data(date_str, conn=c)
    charts = generate_charts(c, d['report_date'], venue=cfg['data'].get('primary_venue', 'binance_perp'))
    d['charts'] = charts
    md = render_markdown(d)
    path = save_report(c, d['report_date'], md, chart_paths=charts)
    click.echo(path)


@cli.command('run')
def run_cmd():
    from btc_analyst.run_live import main
    import asyncio

    click.echo('Starting live loop (scheduler + periodic recompute/report jobs)...')
    asyncio.run(main())


@cli.command('alerts')
@click.option('--active', is_flag=True, default=False)
def alerts_cmd(active):
    c = get_conn(DB_PATH)
    q = 'SELECT id,zone_id,alert_type,created_at,delivery_status,condition_json FROM alerts ORDER BY id DESC LIMIT 50'
    if active:
        q = 'SELECT id,zone_id,alert_type,created_at,delivery_status,condition_json FROM alerts WHERE triggered_at IS NULL ORDER BY id DESC LIMIT 50'
    for r in c.execute(q).fetchall():
        cond = {}
        try:
            cond = json.loads(r[5] or '{}')
        except Exception:
            cond = {}
        click.echo(
            {
                'id': r[0],
                'zone_id': r[1],
                'type': r[2],
                'created_at': r[3],
                'delivery_status': r[4],
                'report': cond.get('report_short'),
            }
        )


@cli.command('backtest')
@click.option('--config', 'cfg', default='bt.yaml')
@click.option('--period', default='2020-01-01:2024-06-30')
def backtest_cmd(cfg, period):
    from backtest.harness import run_walk_forward
    from backtest.reports import build_backtest_report

    c = get_conn(DB_PATH)
    cfg = load_config()
    v = cfg['data'].get('primary_venue', 'binance_perp')
    df = pd.read_sql_query("SELECT open_time,open,high,low,close,volume FROM candles WHERE symbol='BTCUSDT' AND venue=? AND timeframe='4h' ORDER BY open_time", c, params=[v])
    result = run_walk_forward(df)
    artifacts = build_backtest_report(result, out_dir='backtest_results')
    click.echo({'metrics': result['metrics'], 'artifacts': artifacts})


@cli.command('sanity-check')
def sanity_check_cmd():
    c = get_conn(DB_PATH)
    run_migrations(c)
    candles = c.execute('SELECT COUNT(*) FROM candles').fetchone()[0]
    zones = c.execute('SELECT COUNT(*) FROM zones').fetchone()[0]
    reports = c.execute('SELECT COUNT(*) FROM reports').fetchone()[0]
    click.echo({'ok': True, 'candles': candles, 'zones': zones, 'reports': reports})


@cli.command('monitor-once')
def monitor_once_cmd():
    c = get_conn(DB_PATH)
    run_migrations(c)
    cfg = load_config()
    click.echo(run_market_monitor_cycle(c, cfg))


@cli.command('probability-once')
@click.option('--timeframe', default='all')
def probability_once_cmd(timeframe):
    c = get_conn(DB_PATH)
    run_migrations(c)
    cfg = load_config()
    click.echo(compute_probability_snapshot(c, cfg, timeframe=timeframe))


@cli.command('probability-score-retro')
def probability_score_retro_cmd():
    c = get_conn(DB_PATH)
    run_migrations(c)
    click.echo(score_probability_outcomes(c))


@cli.command('probability-state')
@click.option('--timeframe', default='all')
def probability_state_cmd(timeframe):
    c = get_conn(DB_PATH)
    run_migrations(c)
    click.echo(get_probability_score(c, timeframe=timeframe))


@cli.command('probability-explain')
@click.option('--timeframe', default='4h')
def probability_explain_cmd(timeframe):
    c = get_conn(DB_PATH)
    run_migrations(c)
    click.echo(explain_probability(c, timeframe=timeframe))


@cli.command('regime-state')
@click.option('--timeframe', default='all')
def regime_state_cmd(timeframe):
    c = get_conn(DB_PATH)
    run_migrations(c)
    click.echo(get_regime_state(c, timeframe=timeframe))


@cli.command('probability-calibration')
def probability_calibration_cmd():
    c = get_conn(DB_PATH)
    run_migrations(c)
    click.echo(calibration_report(c))


@cli.command('state-snapshot')
@click.option('--json', 'as_json', is_flag=True, default=False)
def state_snapshot_cmd(as_json):
    snap = hermes_get_state()
    snap['probability_4h'] = hermes_get_probability('4h')
    snap['probability_1d'] = hermes_get_probability('1d')
    snap['regime_4h'] = hermes_regime_state('4h')
    snap['crowd'] = hermes_get_crowd_positioning()
    snap['active_setups'] = hermes_get_setups('active')
    if as_json:
        click.echo(json.dumps(snap, indent=2, default=str))
    else:
        click.echo(snap)


if __name__ == '__main__':
    cli()
