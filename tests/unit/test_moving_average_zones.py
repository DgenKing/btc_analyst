from btc_analyst.zones.moving_average import detect_ma_cluster_zones


def test_detect_ma_cluster_zones_emits_all_framework_mas_with_expected_strength_order():
    """Framework lists 20/50/100/200 MAs; detector should emit one zone per MA with increasing macro weight."""
    ma_values = [100000.0, 98000.0, 96000.0, 94000.0]  # 20/50/100/200

    zones = detect_ma_cluster_zones(
        symbol="BTCUSDT",
        timeframe="1d",
        ma_values=ma_values,
        proximity_pct=0.5,
        current_price=97000.0,
    )

    assert len(zones) == 4

    strengths = [z.factors["ma_strength"] for z in zones]
    assert strengths == [0.3, 0.5, 0.75, 1.0]

    # Above current price => resistance; below => support.
    assert zones[0].zone_type == "resistance"  # 100k > 97k
    assert zones[1].zone_type == "resistance"  # 98k > 97k
    assert zones[2].zone_type == "support"     # 96k < 97k
    assert zones[3].zone_type == "support"     # 94k < 97k


def test_detect_ma_cluster_zones_keeps_framework_ma_strength_identity_with_missing_inputs():
    """Framework rule: 20/50/100/200 MA meanings must stay intact even with incomplete MA data."""
    ma_values = [None, 98000.0, 96000.0, 94000.0]  # missing 20 MA; 50/100/200 remain

    zones = detect_ma_cluster_zones(
        symbol="BTCUSDT",
        timeframe="1d",
        ma_values=ma_values,
        proximity_pct=0.5,
        current_price=97000.0,
    )

    assert len(zones) == 3
    # Incomplete-data edge: missing 20 MA should NOT shift 50/100/200 strengths down.
    assert [z.factors["ma_strength"] for z in zones] == [0.5, 0.75, 1.0]
