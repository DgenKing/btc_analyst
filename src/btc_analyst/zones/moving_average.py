from .registry import Zone
def detect_ma_cluster_zones(symbol,timeframe,ma_values,proximity_pct=0.5):
    out=[]
    for v in [x for x in ma_values if x]: out.append(Zone(symbol,v*(1-proximity_pct/100),v*(1+proximity_pct/100),'support','ma_cluster',timeframe,factors={'ma':v}))
    return out
