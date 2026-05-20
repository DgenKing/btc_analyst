from btc_analyst.alerts.engine import run_alert_engine

def test_alert_engine_zone_entry(tmp_path):
    import sqlite3
    db=sqlite3.connect(tmp_path/'a.db')
    db.execute("CREATE TABLE alerts(id INTEGER PRIMARY KEY, created_at INTEGER, zone_id INTEGER, alert_type TEXT, condition_json TEXT, triggered_at INTEGER, triggered_price REAL, delivered_via TEXT, delivery_status TEXT, dedupe_key TEXT UNIQUE)")
    zones=[{'id':1,'price_low':100,'price_high':110}]
    fired=run_alert_engine(db,zones,105)
    assert len(fired)==1
