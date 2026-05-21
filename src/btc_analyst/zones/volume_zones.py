from __future__ import annotations

from .registry import Zone
from btc_analyst.config import load_config
from btc_analyst.indicators.volume_profile import compute_profile


def _zone_type_for_level(level: float, current_price: float) -> str:
    return 'resistance' if float(level) > float(current_price) else 'support'


def zones_from_profile(df, symbol='BTCUSDT', timeframe='1d', bins=50):
    cfg = load_config()
    vp_cfg = ((cfg.get('zones') or {}).get('volume_profile') or {})
    hvn_multiplier = float(vp_cfg.get('hvn_multiplier', 1.5))
    lvn_multiplier = float(vp_cfg.get('lvn_multiplier', 0.5))

    price = float(df['close'].astype(float).iloc[-1])
    p = compute_profile(
        df['close'].to_numpy(),
        df['volume'].to_numpy(),
        bins=bins,
        hvn_multiplier=hvn_multiplier,
        lvn_multiplier=lvn_multiplier,
    )

    out = [
        Zone(
            symbol,
            p['poc'] * 0.999,
            p['poc'] * 1.001,
            _zone_type_for_level(p['poc'], price),
            'vp_poc',
            timeframe,
            factors={'poc': p['poc'], 'vp_strength': 0.8},
        ),
        Zone(
            symbol,
            p['val'] * 0.999,
            p['val'] * 1.001,
            _zone_type_for_level(p['val'], price),
            'vp_val',
            timeframe,
            factors={'val': p['val'], 'vp_strength': 0.6},
        ),
        Zone(
            symbol,
            p['vah'] * 0.999,
            p['vah'] * 1.001,
            _zone_type_for_level(p['vah'], price),
            'vp_vah',
            timeframe,
            factors={'vah': p['vah'], 'vp_strength': 0.6},
        ),
    ]

    mean_vol = float(p.get('mean_bin_volume') or 0.0)
    for lo, hi, vol in p.get('hvns', []):
        vol_ratio = (float(vol) / mean_vol) if mean_vol > 0 else 0.0
        out.append(
            Zone(
                symbol,
                float(lo),
                float(hi),
                _zone_type_for_level((float(lo) + float(hi)) / 2.0, price),
                'vp_hvn',
                timeframe,
                factors={'vp_strength': min(1.0, vol_ratio / 2.0), 'vp_volume_ratio': vol_ratio},
            )
        )

    for lo, hi, _vol in p.get('lvns', []):
        out.append(
            Zone(
                symbol,
                float(lo),
                float(hi),
                'liquidity_void',
                'vp_lvn',
                timeframe,
                factors={'vp_strength': 0.3, 'lvn': True},
            )
        )

    return out
