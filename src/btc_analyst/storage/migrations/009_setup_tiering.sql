ALTER TABLE setups ADD COLUMN tier TEXT;
ALTER TABLE setups ADD COLUMN risk_multiplier REAL;

CREATE TABLE IF NOT EXISTS setup_engine_state (
  state_key TEXT PRIMARY KEY,
  state_value TEXT,
  updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

UPDATE setups SET tier = COALESCE(tier, 'legacy');
UPDATE setups SET risk_multiplier = COALESCE(risk_multiplier, 1.0);

CREATE INDEX IF NOT EXISTS idx_setups_tier_status ON setups(tier, status, created_at DESC);
