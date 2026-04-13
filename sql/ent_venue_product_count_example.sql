-- Example: count Enterprise venue × product rows for churn scope (adjust names to your mart).
-- Replace table/view names after validating with AskWoltAI get_schema + your dbt/Snowflake layout.
-- This file is NOT executed by the API — use scripts/snowflake_rowcount_probe.py or Snowflake UI.

-- Rough scale check (~1500 venues worldwide × several surfaces is plausible; validate in your org.)

SELECT COUNT(*) AS row_count
FROM churn_mart.enterprise_venue_products evp
WHERE evp.is_enterprise = TRUE;  -- placeholder predicate

-- Unique venues in scope:
-- SELECT COUNT(DISTINCT evp.venue_id) AS venue_count FROM churn_mart.enterprise_venue_products evp WHERE ...;
