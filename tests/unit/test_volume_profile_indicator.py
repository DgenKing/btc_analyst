import numpy as np

from btc_analyst.indicators.volume_profile import compute_profile


def test_poc_tracks_highest_volume_bin_in_profile():
    """Framework rule: POC is the price level with the highest traded volume in the selected range."""
    closes = np.array([100.0, 101.0, 102.0, 109.0, 110.0, 111.0], dtype=float)
    volumes = np.array([1.0, 1.0, 1.0, 50.0, 50.0, 50.0], dtype=float)

    profile = compute_profile(closes, volumes, bins=2)

    # With 2 bins over [100,111], the high-price bin is [105.5,111] and carries the max volume.
    expected_poc = (105.5 + 111.0) / 2
    assert profile["poc"] == expected_poc

    # If volume concentration flips to the low-price bin, POC should move there.
    flipped = compute_profile(closes, volumes[::-1], bins=2)
    expected_low_bin_poc = (100.0 + 105.5) / 2
    assert flipped["poc"] == expected_low_bin_poc
