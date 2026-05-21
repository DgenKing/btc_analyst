import sqlite3

from btc_analyst.reports.daily import build_report_data
from btc_analyst.storage.db import run_migrations


def _init_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    run_migrations(conn)
    return conn


def test_source_label_uses_configured_primary_venue(monkeypatch):
    conn = _init_conn()

    monkeypatch.setattr(
        "btc_analyst.reports.daily.load_config",
        lambda: {"data": {"primary_venue": "bybit_perp", "derivatives_venue": "hyperliquid_perp"}, "monitoring": {}},
    )

    data = build_report_data(conn=conn)
    assert data["source_label"] == "Bybit BTCUSDT perp (spot cross-checked)"
