/**
 * Build-time flags, API-related constants, and shared UI config (risk tiers, grouping).
 */

/**
 * Opt-in hardened UI: `VITE_STRICT_PROD=true` at **build** time hides dev-only controls.
 */
export const STRICT_PROD = import.meta.env.VITE_STRICT_PROD === "true";

export const FILTER_NONE = "__none__";

/** AskWoltAI MCP repo — exploration / Snowflake alignment (same link as README). */
export const ASKWOLTAI_MCP_GITHUB_HREF =
  "https://github.com/rajivkhattar-commits/ask-wolt-mcp";

/** Dev-only dry-run inbox for bulk outreach (`preview_to_email`; not the real AM). */
export const DEV_CHURN_PREVIEW_EMAIL = "rajv.khattar@wolt.com";

export const BAND_ORDER: Record<string, number> = {
  lower_concern: 0,
  elevated: 1,
  high_priority: 2,
  critical: 3,
};

/** API expects 0–1; UI uses 0–100 for Sales clarity. Presets align with category band colors. */
export type PresetBand = "lower_concern" | "elevated" | "high_priority" | "critical";

export const PRESETS: readonly { label: string; percent: number; band: PresetBand }[] = [
  { label: "All accounts", percent: 0, band: "lower_concern" },
  { label: "Elevated+", percent: 35, band: "elevated" },
  { label: "High priority+", percent: 55, band: "high_priority" },
  { label: "Critical only", percent: 75, band: "critical" },
];
