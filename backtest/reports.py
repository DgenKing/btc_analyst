from pathlib import Path
import json


def build_backtest_report(result, out_dir='backtest_results'):
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)

    md = p / 'report.md'
    csv = p / 'trades.csv'
    js = p / 'metrics.json'

    metrics = result.get('metrics', {})
    trades = result.get('trades', [])
    wd = result.get('weekday', {})
    rg = result.get('regime', {})

    md.write_text(
        "# Backtest Report\n\n"
        f"Trades: {metrics.get('trades', 0)}\n"
        f"Win rate: {metrics.get('win_rate', 0)}%\n"
        f"Avg R: {metrics.get('avg_r', 0)}\n"
        f"Profit factor: {metrics.get('profit_factor', 0)}\n\n"
        "## Weekday Avg R\n"
        f"{wd}\n\n"
        "## Regime Avg R\n"
        f"{rg}\n"
    )

    if trades:
        keys = list(trades[0].keys())
        header = ','.join(keys) + '\n'
        rows = '\n'.join(','.join(str(t[k]) for k in keys) for t in trades) + '\n'
        csv.write_text(header + rows)
    else:
        csv.write_text('')

    js.write_text(json.dumps({'metrics': metrics, 'weekday': wd, 'regime': rg}, indent=2))
    return {'report': str(md), 'csv': str(csv), 'metrics_json': str(js)}
