import json
import sqlite3
from btc_analyst.setups import engine

def test_b_tier_setup_stays_pending_until_no_a_lockout_bars_elapsed(monkeypatch):
    """Framework rule: leverage/confluence gating keeps B-tier setups non-alertable until configured no-A 4h bars pass."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE zones (id INTEGER PRIMARY KEY, price_low REAL, price_high REAL, zone_type TEXT, score REAL, tier TEXT, status TEXT)")
    conn.execute("CREATE TABLE setups (id INTEGER PRIMARY KEY AUTOINCREMENT, zone_id INTEGER, direction TEXT, reaction_type TEXT, trigger_type TEXT, status TEXT, created_at INTEGER)")
    conn.execute("CREATE TABLE setup_engine_state (state_key TEXT PRIMARY KEY, state_value TEXT, updated_at INTEGER)")
    conn.execute("INSERT INTO zones(id, price_low, price_high, zone_type, score, tier, status) VALUES (1, 99000.0, 99500.0, 'support', 92.0, 'strong', 'active')")
    conn.execute("INSERT INTO zones(id, price_low, price_high, zone_type, score, tier, status) VALUES (2, 101500.0, 102000.0, 'resistance', 88.0, 'strong', 'active')")
    cur_open = 1_700_000_000_000
    one_bar_ms = 4 * 3600 * 1000
    conn.execute("INSERT INTO setup_engine_state(state_key, state_value, updated_at) VALUES ('last_a_setup_4h_bar', ?, 0)", (str(cur_open - one_bar_ms),))
    conn.commit()
    monkeypatch.setattr(engine, "_latest_4h", lambda *_args, **_kwargs: ({"open_time": cur_open, "close": 100000.0}, None))
    monkeypatch.setattr(engine, "_weekend_impulse_context", lambda *_args, **_kwargs: {"ok": False})
    monkeypatch.setattr(engine, "_asia_us_reversal_signal", lambda *_args, **_kwargs: {"active": False})
    monkeypatch.setattr(engine, "_mtf_alignment", lambda *_args, **_kwargs: (True, "partial_alignment", 1.0, {}))
    monkeypatch.setattr(engine, "_atr_daily_pct", lambda *_args, **_kwargs: 2.0)
    monkeypatch.setattr(engine, "_latest_4h_indicators", lambda *_args, **_kwargs: (55.0, 0.1))
    monkeypatch.setattr(engine, "detect_reactions", lambda *_args, **_kwargs: {"type": "acceptance"})
    monkeypatch.setattr(engine, "detect_trigger", lambda *_args, **_kwargs: {"trigger": "reclaim"})
    monkeypatch.setattr(engine, "get_probability_score", lambda *_args, **_kwargs: {"timeframes": {"4h": {"prob_up": 0.6}, "1d": {"prob_up": 0.6}, "1w": {"prob_up": 0.4}}})
    monkeypatch.setattr(engine, "get_regime_state", lambda *_args, **_kwargs: {"timeframes": {"4h": {"regime": "trend"}, "1d": {"regime": "trend"}}})
    persisted = []
    monkeypatch.setattr(engine, "build_setup", lambda zone, entry, stop, t1, t2, reaction, trigger: {"zone_id": zone["id"], "direction": "long", "reaction_type": reaction["type"], "trigger_type": trigger["trigger"], "rr_to_t1": 2.0, "confidence": 80.0})
    monkeypatch.setattr(engine, "persist_setup", lambda _conn, setup: persisted.append(setup))
    cfg = {"data": {"primary_venue": "hyperliquid_perp", "symbol": "BTCUSDC"}, "monitoring": {"diagnostic_min_zone_score": 40.0}, "setups": {"min_rr_t1": 1.5, "atr_daily_max_pct": 5.0, "atr_daily_min_pct": 1.0, "tiering": {"enabled": True, "a_required_factors": 4, "b_required_factors": 3, "b_unlock_after_no_a_4h_bars": 2, "risk_multiplier": {"a": 1.0, "b": 0.5, "c": 0.0}}}}
    result = engine.run_setup_engine(conn, cfg)
    assert len(persisted) >= 1
    assert result["persisted"] == len(persisted)
    for setup in persisted:
        notes = json.loads(setup["notes_json"])
        assert setup["tier"] == "B"
        assert setup["status"] == "pending_b"
        assert notes["b_unlocked"] is False
        assert notes["bars_since_last_a"] == 1


def test_b_tier_setup_unlocks_after_no_a_lockout_bars_elapsed(monkeypatch):
    """Framework rule: selective execution can activate deferred B-tier setups only after the no-A lockout window has elapsed."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE zones (id INTEGER PRIMARY KEY, price_low REAL, price_high REAL, zone_type TEXT, score REAL, tier TEXT, status TEXT)")
    conn.execute("CREATE TABLE setups (id INTEGER PRIMARY KEY AUTOINCREMENT, zone_id INTEGER, direction TEXT, reaction_type TEXT, trigger_type TEXT, status TEXT, created_at INTEGER)")
    conn.execute("CREATE TABLE setup_engine_state (state_key TEXT PRIMARY KEY, state_value TEXT, updated_at INTEGER)")
    conn.execute("INSERT INTO zones(id, price_low, price_high, zone_type, score, tier, status) VALUES (1, 99000.0, 99500.0, 'support', 92.0, 'strong', 'active')")
    conn.execute("INSERT INTO zones(id, price_low, price_high, zone_type, score, tier, status) VALUES (2, 101500.0, 102000.0, 'resistance', 88.0, 'strong', 'active')")
    cur_open = 1_700_000_000_000
    one_bar_ms = 4 * 3600 * 1000
    conn.execute("INSERT INTO setup_engine_state(state_key, state_value, updated_at) VALUES ('last_a_setup_4h_bar', ?, 0)", (str(cur_open - 2 * one_bar_ms),))
    conn.commit()
    monkeypatch.setattr(engine, "_latest_4h", lambda *_args, **_kwargs: ({"open_time": cur_open, "close": 100000.0}, None))
    monkeypatch.setattr(engine, "_weekend_impulse_context", lambda *_args, **_kwargs: {"ok": False})
    monkeypatch.setattr(engine, "_asia_us_reversal_signal", lambda *_args, **_kwargs: {"active": False})
    monkeypatch.setattr(engine, "_mtf_alignment", lambda *_args, **_kwargs: (True, "partial_alignment", 1.0, {}))
    monkeypatch.setattr(engine, "_atr_daily_pct", lambda *_args, **_kwargs: 2.0)
    monkeypatch.setattr(engine, "_latest_4h_indicators", lambda *_args, **_kwargs: (55.0, 0.1))
    monkeypatch.setattr(engine, "detect_reactions", lambda *_args, **_kwargs: {"type": "acceptance"})
    monkeypatch.setattr(engine, "detect_trigger", lambda *_args, **_kwargs: {"trigger": "reclaim"})
    monkeypatch.setattr(engine, "get_probability_score", lambda *_args, **_kwargs: {"timeframes": {"4h": {"prob_up": 0.6}, "1d": {"prob_up": 0.6}, "1w": {"prob_up": 0.4}}})
    monkeypatch.setattr(engine, "get_regime_state", lambda *_args, **_kwargs: {"timeframes": {"4h": {"regime": "trend"}, "1d": {"regime": "trend"}}})
    persisted = []
    monkeypatch.setattr(engine, "build_setup", lambda zone, entry, stop, t1, t2, reaction, trigger: {"zone_id": zone["id"], "direction": "long", "reaction_type": reaction["type"], "trigger_type": trigger["trigger"], "rr_to_t1": 2.0, "confidence": 80.0})
    monkeypatch.setattr(engine, "persist_setup", lambda _conn, setup: persisted.append(setup))
    cfg = {"data": {"primary_venue": "hyperliquid_perp", "symbol": "BTCUSDC"}, "monitoring": {"diagnostic_min_zone_score": 40.0}, "setups": {"min_rr_t1": 1.5, "atr_daily_max_pct": 5.0, "atr_daily_min_pct": 1.0, "tiering": {"enabled": True, "a_required_factors": 4, "b_required_factors": 3, "b_unlock_after_no_a_4h_bars": 2, "risk_multiplier": {"a": 1.0, "b": 0.5, "c": 0.0}}}}
    result = engine.run_setup_engine(conn, cfg)
    assert len(persisted) >= 1
    assert result["persisted"] == len(persisted)
    for setup in persisted:
        notes = json.loads(setup["notes_json"])
        assert setup["tier"] == "B"
        assert setup["status"] == "active"
        assert notes["b_unlocked"] is True
        assert notes["bars_since_last_a"] == 2
