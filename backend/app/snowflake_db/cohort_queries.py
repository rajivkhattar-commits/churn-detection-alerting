"""SQL strings for Enterprise cohort and feature loading."""

ENTERPRISE_VENUES_QUERY = """
SELECT venue_id, merchant_id, market, country_code
FROM churn_mart.enterprise_venues
WHERE is_enterprise = TRUE
"""

ENTERPRISE_VENUE_PRODUCTS_QUERY = """
SELECT ev.venue_id, ev.merchant_id, ev.market, ev.country_code, evp.product_code
FROM churn_mart.enterprise_venues ev
JOIN churn_mart.enterprise_venue_products evp ON ev.venue_id = evp.venue_id
WHERE evp.is_active = TRUE
"""

FEATURE_SNAPSHOT_QUERY = """
SELECT
  venue_id,
  merchant_id,
  market,
  country_code,
  product_code,
  as_of_date,
  orders_7d,
  orders_28d,
  gmv_28d,
  orders_wow_change,
  gmv_mom_change,
  login_days_28d,
  support_tickets_28d,
  config_error_rate_28d,
  menu_sync_failures_28d,
  hours_zero_days_28d,
  peer_gmv_percentile
FROM churn_mart.feature_snapshot_latest
"""
