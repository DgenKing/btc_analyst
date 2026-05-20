CREATE TABLE IF NOT EXISTS market_pulse_snapshots (
  ts INTEGER PRIMARY KEY,
  price REAL,
  rsi_1h REAL,
  macd_1h REAL,
  macd_signal_1h REAL,
  macd_hist_1h REAL,
  macd_hist_slope_1h REAL,
  oi_delta_24h_pct REAL,
  funding_8h REAL,
  candle_body_pct_1h REAL,
  upper_wick_pct_1h REAL,
  lower_wick_pct_1h REAL,
  close_position_pct_1h REAL,
  momentum_score REAL,
  direction_label TEXT,
  confidence TEXT,
  components_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_market_pulse_ts ON market_pulse_snapshots(ts DESC);
