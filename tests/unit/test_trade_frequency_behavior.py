import sqlite3
from datetime import datetime, timezone

from btc_analyst.setups import engine


def test_trade_frequency_caps_qualified_setups_to_two_per_week(monkeypatch):
    """Framework rule: ideal one high-quality setup per week, maximum two qualified setups per week."""

    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE zones (
            id INTEGER PRIMARY KEY,
            price_low REAL,
            price_high REAL,
            zone_type TEXT,
            score REAL,
            tier TEXT,
            status TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE setups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id INTEGER,
            direction TEXT,
            reaction_type TEXT,
            trigger_type TEXT,
            status TEXT,
            created_at INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE setup_engine_state (
            state_key TEXT PRIMARY KEY,
            state_value TEXT,
            updated_at INTEGER
        )
        """
    )

    # Three support zones all qualify in this synthetic scenario.
    conn.executemany(
        "INSERT INTO zones(id, price_low, price_high, zone_type, score, tier, status) VALUES (?, ?, ?, ?, ?, ?, 'active')",
        [
            (1, 99000.0, 99500.0, "support", 92.0, "strong"),
            (2, 98000.0, 98500.0, "support", 91.0, "strong"),
            (3, 97000.0, 97500.0, "support", 90.0, "strong"),
            (10, 101500.0, 102000.0, "resistance", 88.0, "strong"),
            (11, 102500.0, 103000.0, "resistance", 87.0, "strong"),
        ],
    )
    conn.commit()

    monkeypatch.setattr(engine, "_latest_4h", lambda *_args, **_kwargs: ({"open_time": 1, "close": 100000.0}, None))
    monkeypatch.setattr(engine, "_weekend_impulse_context", lambda *_args, **_kwargs: {"ok": False})
    monkeypatch.setattr(engine, "_asia_us_reversal_signal", lambda *_args, **_kwargs: {"active": False})
    monkeypatch.setattr(engine, "_mtf_alignment", lambda *_args, **_kwargs: (True, "full_alignment", 1.0, {}))
    monkeypatch.setattr(engine, "_atr_daily_pct", lambda *_args, **_kwargs: 2.0)
    monkeypatch.setattr(engine, "_latest_4h_indicators", lambda *_args, **_kwargs: (55.0, 0.1))
    monkeypatch.setattr(engine, "detect_reactions", lambda *_args, **_kwargs: {"type": "acceptance"})
    monkeypatch.setattr(engine, "detect_trigger", lambda *_args, **_kwargs: {"trigger": "reclaim"})
    monkeypatch.setattr(engine, "get_probability_score", lambda *_args, **_kwargs: {"timeframes": {"4h": {"prob_up": 0.6}, "1d": {"prob_up": 0.6}, "1w": {"prob_up": 0.6}}})
    monkeypatch.setattr(engine, "get_regime_state", lambda *_args, **_kwargs: {"timeframes": {"4h": {"regime": "trend"}, "1d": {"regime": "trend"}}})

    persisted = []

    def fake_build_setup(zone, entry, stop, t1, t2, reaction, trigger):
        return {
            "zone_id": zone["id"],
            "direction": "long" if zone["zone_type"] == "support" else "short",
            "reaction_type": reaction["type"],
            "trigger_type": trigger["trigger"],
            "rr_to_t1": 2.0,
            "confidence": 80.0,
        }

    def fake_persist_setup(_conn, setup):
        persisted.append(setup)

    monkeypatch.setattr(engine, "build_setup", fake_build_setup)
    monkeypatch.setattr(engine, "persist_setup", fake_persist_setup)

    cfg = {
        "data": {"primary_venue": "hyperliquid_perp", "symbol": "BTCUSDC"},
        "monitoring": {"diagnostic_min_zone_score": 40.0},
        "setups": {
            "min_rr_t1": 1.5,
            "atr_daily_max_pct": 5.0,
            "atr_daily_min_pct": 1.0,
            "tiering": {
                "enabled": True,
                "a_required_factors": 3,
                "b_required_factors": 2,
                "b_unlock_after_no_a_4h_bars": 2,
                "risk_multiplier": {"a": 1.0, "b": 0.5, "c": 0.0},
            },
        },
    }

    engine.run_setup_engine(conn, cfg)

    assert len(persisted) == 2


def test_trade_frequency_respects_existing_weekly_setups_before_persisting_new_ones(monkeypatch):
    """Framework rule: maximum two qualified setups per week applies to cumulative weekly setups, not just this cycle."""

    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE zones (
            id INTEGER PRIMARY KEY,
            price_low REAL,
            price_high REAL,
            zone_type TEXT,
            score REAL,
            tier TEXT,
            status TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE setups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id INTEGER,
            direction TEXT,
            reaction_type TEXT,
            trigger_type TEXT,
            status TEXT,
            created_at INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE setup_engine_state (
            state_key TEXT PRIMARY KEY,
            state_value TEXT,
            updated_at INTEGER
        )
        """
    )

    conn.executemany(
        "INSERT INTO zones(id, price_low, price_high, zone_type, score, tier, status) VALUES (?, ?, ?, ?, ?, ?, 'active')",
        [
            (1, 99000.0, 99500.0, "support", 92.0, "strong"),
            (2, 98000.0, 98500.0, "support", 91.0, "strong"),
            (10, 101500.0, 102000.0, "resistance", 88.0, "strong"),
        ],
    )

    now_ts = int(datetime.now(timezone.utc).timestamp())
    conn.executemany(
        "INSERT INTO setups(zone_id, direction, reaction_type, trigger_type, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (90, "long", "acceptance", "reclaim", "active", now_ts - 3600),
            (91, "short", "rejection", "reject", "active", now_ts - 7200),
        ],
    )
    conn.commit()

    monkeypatch.setattr(engine, "_latest_4h", lambda *_args, **_kwargs: ({"open_time": 1, "close": 100000.0}, None))
    monkeypatch.setattr(engine, "_weekend_impulse_context", lambda *_args, **_kwargs: {"ok": False})
    monkeypatch.setattr(engine, "_asia_us_reversal_signal", lambda *_args, **_kwargs: {"active": False})
    monkeypatch.setattr(engine, "_mtf_alignment", lambda *_args, **_kwargs: (True, "full_alignment", 1.0, {}))
    monkeypatch.setattr(engine, "_atr_daily_pct", lambda *_args, **_kwargs: 2.0)
    monkeypatch.setattr(engine, "_latest_4h_indicators", lambda *_args, **_kwargs: (55.0, 0.1))
    monkeypatch.setattr(engine, "detect_reactions", lambda *_args, **_kwargs: {"type": "acceptance"})
    monkeypatch.setattr(engine, "detect_trigger", lambda *_args, **_kwargs: {"trigger": "reclaim"})
    monkeypatch.setattr(engine, "get_probability_score", lambda *_args, **_kwargs: {"timeframes": {"4h": {"prob_up": 0.6}, "1d": {"prob_up": 0.6}, "1w": {"prob_up": 0.6}}})
    monkeypatch.setattr(engine, "get_regime_state", lambda *_args, **_kwargs: {"timeframes": {"4h": {"regime": "trend"}, "1d": {"regime": "trend"}}})

    persisted = []

    def fake_build_setup(zone, entry, stop, t1, t2, reaction, trigger):
        return {
            "zone_id": zone["id"],
            "direction": "long" if zone["zone_type"] == "support" else "short",
            "reaction_type": reaction["type"],
            "trigger_type": trigger["trigger"],
            "rr_to_t1": 2.0,
            "confidence": 80.0,
        }

    def fake_persist_setup(_conn, setup):
        persisted.append(setup)

    monkeypatch.setattr(engine, "build_setup", fake_build_setup)
    monkeypatch.setattr(engine, "persist_setup", fake_persist_setup)

    cfg = {
        "data": {"primary_venue": "hyperliquid_perp", "symbol": "BTCUSDC"},
        "monitoring": {"diagnostic_min_zone_score": 40.0},
        "setups": {
            "trade_frequency": {"max_qualified_setups_per_week": 2},
            "min_rr_t1": 1.5,
            "atr_daily_max_pct": 5.0,
            "atr_daily_min_pct": 1.0,
            "tiering": {
                "enabled": True,
                "a_required_factors": 3,
                "b_required_factors": 2,
                "b_unlock_after_no_a_4h_bars": 2,
                "risk_multiplier": {"a": 1.0, "b": 0.5, "c": 0.0},
            },
        },
    }

    result = engine.run_setup_engine(conn, cfg)

    assert len(persisted) == 0
    assert result["reasons"].get("trade_frequency_cap_reached", 0) >= 1
