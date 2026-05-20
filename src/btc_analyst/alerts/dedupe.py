def dedupe_key(kind, zone_id, ts):
    return f"{kind}:{zone_id}:{ts}"
