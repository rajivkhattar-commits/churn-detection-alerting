-- Local SQLite persistence (safe for the app to create in dev/tests).
-- Path controlled by LOCAL_SQLITE_PATH in app settings.

CREATE TABLE IF NOT EXISTS score_runs (
    run_id TEXT NOT NULL,
    venue_id TEXT NOT NULL,
    merchant_id TEXT,
    market TEXT,
    country_code TEXT,
    product_code TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    scored_at TEXT NOT NULL,
    risk_score REAL NOT NULL,
    churn_type_probs TEXT,
    model_version TEXT,
    explanation TEXT,
    PRIMARY KEY (run_id, venue_id, product_code)
);

CREATE TABLE IF NOT EXISTS outreach_audit (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    venue_id TEXT NOT NULL,
    merchant_id TEXT,
    market TEXT,
    country_code TEXT,
    product_code TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    template_id TEXT,
    payload_summary TEXT,
    created_at TEXT NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS explanation_feedback (
    id TEXT PRIMARY KEY,
    venue_id TEXT NOT NULL,
    product_code TEXT NOT NULL,
    run_id TEXT NOT NULL,
    hypothesis_index INTEGER,
    rating TEXT NOT NULL,
    comment TEXT,
    submitted_at TEXT NOT NULL,
    submitter_id TEXT
);

CREATE TABLE IF NOT EXISTS improvement_metrics_daily (
    metric_date TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    segment TEXT NOT NULL,
    PRIMARY KEY (metric_date, metric_name, segment)
);
