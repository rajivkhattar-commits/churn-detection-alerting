-- Enterprise restaurant venue scope (DBA / analytics-owned template).
-- The application does not execute this file against Snowflake.
--
-- Replace raw.* / churn_mart.* names using AskWoltAI MCP: get_schema, then ask_wolt
-- for ENT venue definition. See sql/mcp_workflow.txt. Export prose to ENTERPRISE_DEFINITION_JSON.

CREATE OR REPLACE VIEW churn_mart.enterprise_venues AS
SELECT
    v.venue_id::VARCHAR AS venue_id,
    v.merchant_id::VARCHAR AS merchant_id,
    v.market::VARCHAR AS market,
    v.country_code::VARCHAR(2) AS country_code,
    v.is_enterprise::BOOLEAN AS is_enterprise
FROM raw.dim_venue v
WHERE v.is_enterprise = TRUE
  AND v.is_test = FALSE;

-- Product entitlements per venue (one row per venue × Wolt surface: classic, wolt_plus,
-- takeaway_pickup, drive, wolt_for_work, preorder — align with ProductCode / enterprise_churn_definition.json).
CREATE OR REPLACE VIEW churn_mart.enterprise_venue_products AS
SELECT
    e.venue_id,
    e.merchant_id,
    e.market,
    e.country_code,
    p.product_code::VARCHAR AS product_code,
    p.is_active::BOOLEAN AS is_active
FROM churn_mart.enterprise_venues e
JOIN raw.fact_venue_product_entitlement p
  ON e.venue_id = p.venue_id
WHERE p.is_active = TRUE;
