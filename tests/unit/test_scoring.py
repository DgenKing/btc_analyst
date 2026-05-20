from btc_analyst.zones.registry import Zone
from btc_analyst.scoring.scorer import score_zone

def test_score_zone_basic():
    cfg={"scoring":{"weights":{"horizontal_sr":25,"volume_profile":20,"ma_confluence":10,"market_structure":15},"tier_thresholds":{"strong":80,"medium":60,"weak":40},"multipliers":{"trend_with":1.15}}}
    z=Zone('BTCUSDT',100,101,'support','horizontal','4h')
    z=score_zone(z,cfg,{"regime":"range"})
    assert z.score>0
