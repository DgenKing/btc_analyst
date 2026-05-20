from .registry import Zone
from btc_analyst.indicators.volume_profile import compute_profile
def zones_from_profile(df,symbol='BTCUSDT',timeframe='1d',bins=50):
    p=compute_profile(df['close'].to_numpy(),df['volume'].to_numpy(),bins=bins)
    return [Zone(symbol,p['poc']*0.999,p['poc']*1.001,'support','vp_poc',timeframe,factors={'poc':p['poc']}),Zone(symbol,p['val']*0.999,p['val']*1.001,'support','vp_val',timeframe,factors={'val':p['val']}),Zone(symbol,p['vah']*0.999,p['vah']*1.001,'resistance','vp_vah',timeframe,factors={'vah':p['vah']})]
