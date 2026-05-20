import json

from btc_analyst.sentiment.aggregator import aggregate_label_from_signals, refresh_crowd_positioning


def test_aggregate_label_extreme_long():
    cfg = {
        "sentiment": {
            "extreme_thresholds": {
                "funding_8h_abs": 0.0005,
                "long_short_ratio_high": 2.0,
                "long_short_ratio_low": 0.5,
                "fear_greed_extreme_low": 20,
                "fear_greed_extreme_high": 80,
            },
            "aggregate_rule": {"extreme_signals_required": 3, "mild_signals_required": 2},
        }
    }
    row = {
        "bybit_funding_8h": 0.0008,
        "bybit_long_short_ratio": 2.4,
        "okx_long_short_ratio": 2.1,
        "fear_greed_value": 84,
        "coinglass_long_short_aggregate": 2.2,
    }
    label, extreme, detail = aggregate_label_from_signals(row, cfg)
    assert label == "extreme_long_crowd"
    assert extreme == 1
    assert detail["extreme_long"] >= 3


def test_aggregate_label_neutral_when_sparse():
    cfg = {
        "sentiment": {
            "extreme_thresholds": {
                "funding_8h_abs": 0.0005,
                "long_short_ratio_high": 2.0,
                "long_short_ratio_low": 0.5,
                "fear_greed_extreme_low": 20,
                "fear_greed_extreme_high": 80,
            },
            "aggregate_rule": {"extreme_signals_required": 3, "mild_signals_required": 2},
        }
    }
    label, extreme, detail = aggregate_label_from_signals({}, cfg)
    assert label == "neutral"
    assert extreme == 0
    assert detail["signals_total"] == 0


def test_refresh_crowd_positioning_survives_source_failure(tmp_path):
    import sqlite3

    db = sqlite3.connect(str(tmp_path / "x.db"))
    db.executescript(
        """
        CREATE TABLE funding(symbol TEXT, venue TEXT, funding_time INTEGER, funding_rate REAL, PRIMARY KEY(symbol, venue, funding_time));
        CREATE TABLE open_interest(symbol TEXT, venue TEXT, ts INTEGER, oi REAL, PRIMARY KEY(symbol, venue, ts));
        CREATE TABLE crowd_positioning_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            bybit_funding_8h REAL,
            bybit_oi_24h_delta_pct REAL,
            bybit_long_short_ratio REAL,
            okx_long_short_ratio REAL,
            coinglass_funding_aggregate REAL,
            coinglass_oi_aggregate REAL,
            coinglass_long_short_aggregate REAL,
            coinglass_liquidations_24h_long_usd REAL,
            coinglass_liquidations_24h_short_usd REAL,
            fear_greed_value INTEGER,
            fear_greed_label TEXT,
            reddit_sentiment_score REAL,
            btc_dominance_pct REAL,
            aggregate_label TEXT NOT NULL,
            extreme_flag INTEGER NOT NULL DEFAULT 0,
            sources_available_json TEXT NOT NULL
        );
        """
    )
    db.execute("INSERT INTO funding(symbol, venue, funding_time, funding_rate) VALUES ('BTCUSDT','bybit_perp',100,0.0001)")
    db.execute("INSERT INTO funding(symbol, venue, funding_time, funding_rate) VALUES ('BTCUSDT','bybit_perp',200,0.0002)")
    db.execute("INSERT INTO open_interest(symbol, venue, ts, oi) VALUES ('BTCUSDT','bybit_perp',100,1000)")
    db.execute("INSERT INTO open_interest(symbol, venue, ts, oi) VALUES ('BTCUSDT','bybit_perp',200,1100)")
    db.commit()

    cfg = {
        "sentiment": {
            "enabled": True,
            "sources": {
                "bybit_longshort": {"enabled": True},
                "okx_longshort": {"enabled": True},
                "coinglass": {"enabled": True, "api_key_env": "COINGLASS_API_KEY", "base_url": "https://open-api-v4.coinglass.com", "cache_ttl_minutes": 60},
                "fear_greed": {"enabled": True},
                "reddit": {"enabled": False, "user_agent": "btc_analyst/1.0 by /u/test"},
                "coingecko": {"enabled": True},
            },
            "extreme_thresholds": {
                "funding_8h_abs": 0.0005,
                "long_short_ratio_high": 2.0,
                "long_short_ratio_low": 0.5,
                "fear_greed_extreme_low": 20,
                "fear_greed_extreme_high": 80,
            },
            "aggregate_rule": {"extreme_signals_required": 3, "mild_signals_required": 2},
        }
    }

    # monkeypatch by replacing module-level fetchers
    import btc_analyst.sentiment.aggregator as ag

    ag.fetch_bybit_longshort = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail"))
    ag.fetch_okx_longshort = lambda *args, **kwargs: {"long_short_ratio": 1.1}
    ag.fetch_fear_greed = lambda *args, **kwargs: {"value": 52, "label": "Neutral"}
    ag.fetch_coingecko_context = lambda *args, **kwargs: {"btc_dominance_pct": 55.1}
    ag.fetch_reddit_sentiment = lambda *args, **kwargs: None

    class DummyCg:
        def __init__(self, *args, **kwargs):
            pass

        def status(self):
            return None

        def funding_oi_weighted(self):
            return None

        def oi_aggregate(self):
            return None

        def long_short_aggregate(self):
            return None

        def liquidations_aggregated(self):
            return None

    ag.CoinGlassClient = DummyCg

    out = refresh_crowd_positioning(db, cfg)
    assert out["ok"] is True
    assert out["snapshot"]["aggregate_label"] in {"neutral", "mild_long", "mild_short", "extreme_long_crowd", "extreme_short_crowd"}
    saved = db.execute("SELECT sources_available_json FROM crowd_positioning_snapshots ORDER BY id DESC LIMIT 1").fetchone()
    assert saved is not None
    avail = json.loads(saved[0])
    assert avail["okx_longshort"] is True
