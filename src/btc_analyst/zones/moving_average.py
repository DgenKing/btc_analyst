from __future__ import annotations

from .registry import Zone


def detect_ma_cluster_zones(symbol, timeframe, ma_values, proximity_pct=0.5, current_price=None):
    out = []
    strength_by_index = {0: 0.3, 1: 0.5, 2: 0.75, 3: 1.0}
    for idx, v in enumerate([x for x in ma_values if x == x and x is not None]):
        ma = float(v)
        if current_price is None:
            zone_type = 'support'
        else:
            zone_type = 'resistance' if ma > float(current_price) else 'support'
        out.append(
            Zone(
                symbol,
                ma * (1 - proximity_pct / 100),
                ma * (1 + proximity_pct / 100),
                zone_type,
                'ma_cluster',
                timeframe,
                factors={
                    'ma': ma,
                    'ma_strength': strength_by_index.get(idx, 0.3),
                },
            )
        )
    return out
