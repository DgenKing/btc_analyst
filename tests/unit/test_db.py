from btc_analyst.storage.db import get_conn, run_migrations

def test_init_tables(tmp_path):
    db=tmp_path/'x.db'; c=get_conn(str(db)); run_migrations(c)
    tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert 'candles' in tables
    assert 'zones' in tables
    assert 'reports' in tables
    assert 'crowd_positioning_snapshots' in tables
