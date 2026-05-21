from btc_analyst.alerts.engine import run_alert_engine


def _create_alerts_table(db):
    db.execute(
        "CREATE TABLE alerts(id INTEGER PRIMARY KEY, created_at INTEGER, zone_id INTEGER, alert_type TEXT, condition_json TEXT, triggered_at INTEGER, triggered_price REAL, delivered_via TEXT, delivery_status TEXT, dedupe_key TEXT UNIQUE)"
    )


def test_alert_engine_zone_entry(tmp_path):
    import sqlite3

    db = sqlite3.connect(tmp_path / 'a.db')
    _create_alerts_table(db)
    zones = [{'id': 1, 'price_low': 100, 'price_high': 110, 'zone_type': 'support'}]
    fired = run_alert_engine(db, zones, 105, cfg={'alerts': {'dedupe_window_minutes': 60}})
    assert len(fired) == 1


def test_alert_engine_zone_entry_dedupes_within_window(tmp_path):
    import sqlite3

    db = sqlite3.connect(tmp_path / 'b.db')
    _create_alerts_table(db)
    zones = [{'id': 1, 'price_low': 100, 'price_high': 110, 'zone_type': 'support'}]

    first = run_alert_engine(db, zones, 105, cfg={'alerts': {'dedupe_window_minutes': 60}})
    second = run_alert_engine(db, zones, 106, cfg={'alerts': {'dedupe_window_minutes': 60}})

    count = db.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='zone_entry' AND zone_id=1").fetchone()[0]
    assert len(first) == 1
    assert len(second) == 0
    assert count == 1
