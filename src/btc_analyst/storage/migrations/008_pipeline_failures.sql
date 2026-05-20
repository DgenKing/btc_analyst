CREATE TABLE IF NOT EXISTS pipeline_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    component TEXT NOT NULL,
    error_type TEXT,
    error_message TEXT NOT NULL,
    context_json TEXT,
    dedupe_key TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    recovered_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_pipeline_failures_ts ON pipeline_failures(ts DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_failures_component_ts ON pipeline_failures(component, ts DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pipeline_failures_dedupe ON pipeline_failures(dedupe_key);
