from btc_analyst.scoring.tiers import tier_from_score


def test_strong_tier_requires_score_at_or_above_70_threshold():
    """Framework rule: high-probability/strong setups begin at the configured strong threshold (70)."""
    cfg = {
        "scoring": {
            "tier_thresholds": {"strong": 70, "medium": 50, "weak": 30},
        }
    }

    assert tier_from_score(69.99, cfg) == "medium"
    assert tier_from_score(70.00, cfg) == "strong"


def test_medium_weak_noise_tiers_respect_exact_threshold_boundaries():
    """Framework rule: only sufficiently scored setups should graduate from noise->weak->medium tiers."""
    cfg = {
        "scoring": {
            "tier_thresholds": {"strong": 70, "medium": 50, "weak": 30},
        }
    }

    # Boundary inclusions.
    assert tier_from_score(50.00, cfg) == "medium"
    assert tier_from_score(30.00, cfg) == "weak"

    # "Should NOT fire" into higher tiers when just below boundaries.
    assert tier_from_score(49.99, cfg) == "weak"
    assert tier_from_score(29.99, cfg) == "noise"
