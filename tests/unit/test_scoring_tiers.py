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
