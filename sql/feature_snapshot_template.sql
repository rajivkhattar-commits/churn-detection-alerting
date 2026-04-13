-- Feature snapshot query template (DBA / analytics-owned).
-- The application does not execute this file against Snowflake automatically.
-- Discover real fact table names via AskWoltAI get_schema; validate joins with CANONICAL_JOINS_JSON.

CREATE OR REPLACE VIEW churn_mart.feature_snapshot_latest AS
SELECT
    evp.venue_id,
    evp.merchant_id,
    evp.market,
    evp.country_code,
    evp.product_code,
    CURRENT_DATE() AS as_of_date,
    -- Example placeholders — replace with real metrics:
    COALESCE(u.orders_7d, 0) AS orders_7d,
    COALESCE(u.orders_28d, 0) AS orders_28d,
    COALESCE(u.gmv_28d, 0) AS gmv_28d,
    COALESCE(u.orders_wow_change, 0) AS orders_wow_change,
    COALESCE(u.gmv_mom_change, 0) AS gmv_mom_change,
    COALESCE(u.login_days_28d, 0) AS login_days_28d,
    COALESCE(u.support_tickets_28d, 0) AS support_tickets_28d,
    COALESCE(c.config_error_rate_28d, 0) AS config_error_rate_28d,
    COALESCE(c.menu_sync_failures_28d, 0) AS menu_sync_failures_28d,
    COALESCE(v.hours_zero_days_28d, 0) AS hours_zero_days_28d,
    COALESCE(u.peer_gmv_percentile, 50) AS peer_gmv_percentile
FROM churn_mart.enterprise_venue_products evp
LEFT JOIN churn_mart.agg_venue_usage_28d u
  ON evp.venue_id = u.venue_id AND evp.product_code = u.product_code
LEFT JOIN churn_mart.agg_venue_config_health_28d c
  ON evp.venue_id = c.venue_id
LEFT JOIN churn_mart.agg_venue_operational_28d v
  ON evp.venue_id = v.venue_id;
