import json, time

def save_alert(conn, zone_id, alert_type, condition, dedupe_key):
    conn.execute("INSERT OR IGNORE INTO alerts(created_at,zone_id,alert_type,condition_json,delivery_status,dedupe_key) VALUES(?,?,?,?,?,?)", (int(time.time()), zone_id, alert_type, json.dumps(condition), 'pending', dedupe_key))
    conn.commit()
