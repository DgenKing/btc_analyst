from .registry import Zone
from btc_analyst.indicators.structure import find_swing_highs, find_swing_lows

def detect_horizontal_zones(df,timeframe='4h',symbol='BTCUSDT'):
    hs=find_swing_highs(df['high'].tolist(),3); ls=find_swing_lows(df['low'].tolist(),3); out=[]
    for _,p in hs[-5:]: out.append(Zone(symbol,p*0.998,p*1.002,'resistance','horizontal',timeframe,factors={'touches':1}))
    for _,p in ls[-5:]: out.append(Zone(symbol,p*0.998,p*1.002,'support','horizontal',timeframe,factors={'touches':1}))
    return out
