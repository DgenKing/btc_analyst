import pandas as pd

from btc_analyst.zones.volume_zones import zones_from_profile


def test_hvn_levels_become_directional_support_or_resistance_by_price_position(monkeypatch):
    """Framework rule: HVNs represent acceptance zones that act as support below price and resistance above price."""

    monkeypatch.setattr("btc_analyst.zones.volume_zones.load_config", lambda: {"zones": {"volume_profile": {"hvn_multiplier": 1.5, "lvn_multiplier": 0.5}}})
    monkeypatch.setattr(
        "btc_analyst.zones.volume_zones.compute_profile",
        lambda *_args, **_kwargs: {
            "poc": 105.0,
            "val": 95.0,
            "vah": 110.0,
            "hvns": [(90.0, 92.0, 300.0), (108.0, 109.0, 280.0)],
            "lvns": [],
            "mean_bin_volume": 100.0,
        },
    )

    df = pd.DataFrame({"close": [98.0, 100.0], "volume": [10.0, 20.0]})
    zones = zones_from_profile(df, symbol="BTCUSDT", timeframe="4h", bins=10)

    hvn_zones = [z for z in zones if z.source == "vp_hvn"]
    assert len(hvn_zones) == 2

    below_price = next(z for z in hvn_zones if z.price_high <= 92.0)
    above_price = next(z for z in hvn_zones if z.price_low >= 108.0)

    assert below_price.zone_type == "support"
    assert above_price.zone_type == "resistance"
    assert below_price.factors["vp_volume_ratio"] == 3.0
    assert above_price.factors["vp_volume_ratio"] == 2.8
