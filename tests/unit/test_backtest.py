from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from backtest.harness import run_walk_forward


def _candles(count: int, start_price: float = 100000.0) -> pd.DataFrame:
    rows = []
    ts = datetime(2026, 5, 18, 0, 0, tzinfo=timezone.utc)
    for i in range(count):
        price = start_price + i * 10.0
        rows.append(
            {
                "open_time": int((ts + timedelta(hours=i)).timestamp() * 1000),
                "open": price,
                "high": price + 20.0,
                "low": price - 20.0,
                "close": price + 5.0,
                "volume": 1.0,
            }
        )
    return pd.DataFrame(rows)


def test_walk_forward_returns_empty_metrics_when_insufficient_history():
    result = run_walk_forward(_candles(60))

    assert result["trades"] == []
    assert result["metrics"] == {
        "trades": 0,
        "win_rate": 0,
        "avg_r": 0,
        "profit_factor": 0,
    }


def test_walk_forward_generates_trades_and_aggregates_weekday_regime_metrics():
    result = run_walk_forward(_candles(96))

    assert len(result["trades"]) > 0
    assert result["metrics"]["trades"] == len(result["trades"])
    assert set(result["weekday"].keys()) == set(range(7))
    assert "range" in result["regime"]
    assert all("realised_r" in trade for trade in result["trades"])
