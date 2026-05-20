CREATE TABLE IF NOT EXISTS liquidation_heatmap_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  snapshot_time INTEGER NOT NULL,
  price_bucket_low REAL NOT NULL,
  price_bucket_high REAL NOT NULL,
  long_liq_usd REAL NOT NULL DEFAULT 0,
  short_liq_usd REAL NOT NULL DEFAULT 0,
  net_liq_usd REAL NOT NULL DEFAULT 0,
  source TEXT NOT NULL DEFAULT 'hyperliquid'
);
CREATE INDEX IF NOT EXISTS idx_liq_heatmap_time ON liquidation_heatmap_snapshots(snapshot_time DESC);

CREATE TABLE IF NOT EXISTS hyperliquid_addresses (
  address TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  last_seen_ts INTEGER NOT NULL
);
