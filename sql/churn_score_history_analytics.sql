-- Separate table for historical churn scores — Analytics / warehouse load.
-- This application does NOT INSERT into Snowflake; partners export JSON/CSV from the API
-- or a batch job and bulk-load into this table (COPY INTO, Snowpipe, dbt, etc.).
--
-- Align column names with data/score_history_upload_example.csv

CREATE TABLE IF NOT EXISTS analytics.churn_risk_score_history (
    run_id VARCHAR(64) NOT NULL,
    venue_id VARCHAR(128) NOT NULL,
    merchant_id VARCHAR(128),
    market VARCHAR(256),
    country_code VARCHAR(2),
    product_code VARCHAR(32) NOT NULL,
    as_of_date DATE NOT NULL,
    scored_at TIMESTAMP_TZ NOT NULL,
    risk_score FLOAT NOT NULL,
    churn_type_hard_prob FLOAT,
    churn_type_soft_prob FLOAT,
    churn_type_operational_prob FLOAT,
    model_version VARCHAR(64),
    explanation_json VARIANT,
    source_system VARCHAR(64) DEFAULT 'churn_detection_api_export',
    ingested_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

COMMENT ON TABLE analytics.churn_risk_score_history IS
    'Point-in-time churn risk scores for ENT venues × product; loaded by Analytics, not by the detection API.';
