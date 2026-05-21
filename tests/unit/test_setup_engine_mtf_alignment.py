import pandas as pd

from btc_analyst.setups import engine


def test_mtf_alignment_requires_12h_and_8h_agreement_when_daily_is_neutral(monkeypatch):
    """Framework rule: with neutral HTF context, trade direction needs lower-timeframe confluence before execution."""

    def fake_read_sql_query(*args, **kwargs):
        return pd.DataFrame(
            [{"open_time": 1, "high": 110.0, "low": 90.0, "close": 100.0}]
        )

    monkeypatch.setattr(engine.pd, "read_sql_query", fake_read_sql_query)

    def run_case(labels):
        seq = iter(labels)

        def fake_trend_from_df(_df, _timeframe):
            return next(seq)

        monkeypatch.setattr(engine, "_trend_from_df", fake_trend_from_df)
        return engine._mtf_alignment(conn=None, direction="long", venue="binance_perp")

    aligned, label, multiplier, snapshot = run_case(["neutral", "bull", "bull", "neutral"])
    assert aligned is True
    assert label == "htf_neutral_with_ltf_align"
    assert multiplier == 0.8
    assert snapshot == {"daily": "neutral", "h12": "bull", "h8": "bull", "h4": "neutral"}

    aligned_bad, label_bad, _mult_bad, snapshot_bad = run_case(["neutral", "bull", "bear", "bull"])
    assert aligned_bad is False
    assert label_bad == "daily_neutral_no_ltf_align"
    assert snapshot_bad == {"daily": "neutral", "h12": "bull", "h8": "bear", "h4": "bull"}
