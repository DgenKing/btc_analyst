from dataclasses import dataclass, asdict
import json, time

@dataclass
class Zone:
    symbol:str
    price_low:float
    price_high:float
    zone_type:str
    source:str
    timeframe:str
    score:float=0.0
    tier:str='noise'
    status:str='active'
    factors:dict|None=None
    invalidation_price:float|None=None
    notes:str|None=None

def merge_overlapping_zones(zones):
    if not zones: return []
    zones=sorted(zones,key=lambda z:(z.zone_type,z.price_low))
    out=[]
    for z in zones:
        if not out or out[-1].zone_type!=z.zone_type or out[-1].source!=z.source or z.price_low>out[-1].price_high:
            out.append(z); continue
        m=out[-1]; m.price_low=min(m.price_low,z.price_low); m.price_high=max(m.price_high,z.price_high); m.factors={**(m.factors or {}), **(z.factors or {})}
    return out

def upsert_zones(conn,zones):
    now=int(time.time())
    # Keep active set fresh: archive prior active zones for the same symbol before writing new batch.
    symbols = sorted({z.symbol for z in zones}) if zones else []
    for sym in symbols:
        conn.execute("UPDATE zones SET status='consumed', last_updated=? WHERE symbol=? AND status='active'", (now, sym))
    for z in merge_overlapping_zones(zones):
        d=asdict(z)
        conn.execute("INSERT INTO zones(detected_at,last_updated,symbol,price_low,price_high,zone_type,source,timeframe,score,tier,status,factors_json,invalidation_price,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (now,now,d['symbol'],d['price_low'],d['price_high'],d['zone_type'],d['source'],d['timeframe'],d['score'],d['tier'],d['status'],json.dumps(d.get('factors') or {}),d['invalidation_price'],d['notes']))
    conn.commit()
