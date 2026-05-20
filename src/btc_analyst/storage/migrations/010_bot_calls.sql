CREATE TABLE IF NOT EXISTS bot_calls (
  id INTEGER PRIMARY KEY,
  ts INTEGER NOT NULL,
  source TEXT,
  direction TEXT,
  conviction INTEGER,
  price_at_call REAL,
  evidence_json TEXT,
  predicted_horizon_h INTEGER,
  actual_close_price REAL,
  realized_at INTEGER,
  hit INTEGER,
  realized_r_multiple REAL
);

CREATE INDEX IF NOT EXISTS idx_bot_calls_pending ON bot_calls(realized_at, ts);
CREATE INDEX IF NOT EXISTS idx_bot_calls_source_ts ON bot_calls(source, ts DESC);
