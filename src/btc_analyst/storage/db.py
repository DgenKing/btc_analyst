
import sqlite3
from pathlib import Path

MIGRATIONS=["001_market_data.sql","002_derived_analytics.sql","003_backtest.sql","004_sentiment.sql","005_market_monitoring.sql","006_hyperliquid_heatmap.sql","007_probability_scorer.sql","008_pipeline_failures.sql","009_setup_tiering.sql","010_bot_calls.sql"]

def get_conn(db_path:str):
    p=Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(str(p))
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def run_migrations(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS _migrations(name TEXT PRIMARY KEY, applied_at INTEGER DEFAULT (strftime('%s','now')))" )
    cur=conn.cursor()
    mdir=Path(__file__).parent/'migrations'
    for m in MIGRATIONS:
        if cur.execute("SELECT 1 FROM _migrations WHERE name=?",(m,)).fetchone():
            continue
        cur.executescript((mdir/m).read_text())
        cur.execute("INSERT INTO _migrations(name) VALUES (?)",(m,))
    conn.commit()
