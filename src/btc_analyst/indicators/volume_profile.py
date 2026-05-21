from __future__ import annotations

import numpy as np


def compute_profile(closes, volumes, bins=50, hvn_multiplier=1.5, lvn_multiplier=0.5):
    h, e = np.histogram(closes, bins=bins, weights=volumes)
    i = int(np.argmax(h))

    mean_vol = float(np.mean(h)) if len(h) else 0.0
    hvn_cutoff = mean_vol * float(hvn_multiplier)
    lvn_cutoff = mean_vol * float(lvn_multiplier)

    hvns = []
    lvns = []
    for idx, vol in enumerate(h.tolist()):
        lo = float(e[idx])
        hi = float(e[idx + 1])
        v = float(vol)
        if mean_vol > 0 and v >= hvn_cutoff:
            hvns.append((lo, hi, v))
        if mean_vol > 0 and v <= lvn_cutoff:
            lvns.append((lo, hi, v))

    return {
        'poc': float((e[i] + e[i + 1]) / 2),
        'vah': float(e[min(len(e) - 2, i + 1)]),
        'val': float(e[max(0, i - 1)]),
        'hist': h.tolist(),
        'edges': e.tolist(),
        'hvns': hvns,
        'lvns': lvns,
        'mean_bin_volume': mean_vol,
    }
