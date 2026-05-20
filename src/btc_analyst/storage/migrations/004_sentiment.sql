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
CREATE INDEX idx_crowd_ts ON crowd_positioning_snapshots(ts DESC);
