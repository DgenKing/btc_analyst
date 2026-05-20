CREATE TABLE IF NOT EXISTS market_regime_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time INTEGER NOT NULL,
    timeframe TEXT NOT NULL,
    regime TEXT NOT NULL,
    adx REAL,
    hurst REAL,
    atr_pct REAL,
    atr_regime TEXT,
    bb_width_pct REAL,
    bb_squeeze INTEGER DEFAULT 0,
    confidence REAL
);
CREATE INDEX IF NOT EXISTS idx_regime_tf_time ON market_regime_snapshots(timeframe, snapshot_time DESC);

CREATE TABLE IF NOT EXISTS direction_probability_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time INTEGER NOT NULL,
    timeframe TEXT NOT NULL,
    regime_id INTEGER,
    prob_up REAL NOT NULL,
    prob_down REAL NOT NULL,
    prob_sideways REAL NOT NULL,
    raw_score_up REAL,
    raw_score_down REAL,
    raw_score_sideways REAL,
    signal_breakdown TEXT,
    weights_used TEXT,
    commentary TEXT,
    confidence_score REAL,
    outcome TEXT DEFAULT NULL,
    outcome_time INTEGER DEFAULT NULL,
    outcome_pct_change REAL DEFAULT NULL,
    brier_score REAL DEFAULT NULL,
    log_loss REAL DEFAULT NULL,
    FOREIGN KEY(regime_id) REFERENCES market_regime_snapshots(id)
);
CREATE INDEX IF NOT EXISTS idx_prob_tf_time ON direction_probability_snapshots(timeframe, snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_prob_outcome_pending ON direction_probability_snapshots(outcome, timeframe, snapshot_time);

CREATE TABLE IF NOT EXISTS signal_accuracy_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_name TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    regime TEXT,
    day_of_week INTEGER,
    correct_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    accuracy_rate REAL,
    contribution_correctness REAL,
    last_updated INTEGER,
    UNIQUE(signal_name, timeframe, regime, day_of_week)
);

CREATE TABLE IF NOT EXISTS model_calibration_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    eval_date INTEGER NOT NULL,
    timeframe TEXT NOT NULL,
    sample_size INTEGER,
    brier_score REAL,
    log_loss REAL,
    accuracy_at_50pct_threshold REAL,
    accuracy_at_60pct_threshold REAL,
    accuracy_at_70pct_threshold REAL,
    reliability_curve TEXT,
    calibration_intercept REAL,
    calibration_slope REAL
);
CREATE INDEX IF NOT EXISTS idx_calibration_tf_date ON model_calibration_metrics(timeframe, eval_date DESC);
