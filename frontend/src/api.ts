const base = "";

export type AtRiskItem = {
  brand_name: string | null;
  city: string | null;
  country_code: string | null;
  venue_id: string;
  merchant_id: string | null;
  market: string | null;
  venue_display_name: string | null;
  volume_segment: string | null;
  volume_segment_label: string;
  /** Order count, last 90 days (venue-level). */
  orders_90d: number | null;
  product: string;
  product_display: string;
  churn_likelihood: number;
  risk_score: number;
  risk_band_label: string;
  risk_band_key: string;
  churn_reason_summary: string;
  ai_hypothesis: string | null;
  exploration_tips: string;
  churn_type_probs: Record<string, number>;
  run_id: string;
};

export type VenueDetail = {
  brand_name: string | null;
  city: string | null;
  venue_id: string;
  product: string;
  venue_display_name: string | null;
  market: string | null;
  country_code: string | null;
  volume_segment: string | null;
  volume_segment_label: string;
  /** Order count, last 90 days (venue-level). */
  orders_90d: number | null;
  churn_reason_summary: string;
  product_display: string;
  risk_band_label: string;
  risk_band_key: string;
  risk_band_detail: string;
  exploration_tips: string;
  score_meaning: string;
  churn_type_help: string;
  latest: {
    risk_score: number;
    churn_type_probs: Record<string, number>;
    run_id: string;
    as_of_date: string;
    scored_at: string;
  };
  explanation: Record<string, unknown> | null;
  history: unknown[];
};

export type UiCopy = {
  product_labels: Record<string, string>;
  score_meaning: string;
  churn_type_help: string;
};

export async function fetchUiCopy(): Promise<UiCopy> {
  const r = await fetch(`${base}/api/ui/copy`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchAtRisk(minRisk = 0): Promise<AtRiskItem[]> {
  const r = await fetch(`${base}/api/at-risk?min_risk=${minRisk}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchVenue(venueId: string, product: string): Promise<VenueDetail> {
  const r = await fetch(
    `${base}/api/venues/${encodeURIComponent(venueId)}?product=${encodeURIComponent(product)}`
  );
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

/** Reload snapshots + venue enrichment from disk, re-score all rows (matches UI Refresh). */
export async function refreshServerData(): Promise<{
  ok: boolean;
  snapshots: number;
  scored: number;
  run_ids: string[];
}> {
  const r = await fetch(`${base}/api/refresh`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function runScore(venueIds?: string[]) {
  const r = await fetch(`${base}/api/score/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ venue_ids: venueIds ?? null }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function dryRunOutreach(body: Record<string, unknown>) {
  const r = await fetch(`${base}/api/outreach`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

/**
 * Dev dry run: 1 summary email + 1 Slack digest. Email body groups AM templates by venue.
 * Response includes production-equivalent email/slack counts (one per venue×product surface).
 */
export async function bulkPreviewOutreach(body: {
  preview_to_email: string;
  template_id?: string;
  slack_channel_or_user?: string | null;
  rows: Array<{
    venue_id: string;
    product: string;
    market?: string | null;
    country_code?: string | null;
  }>;
}) {
  const r = await fetch(`${base}/api/outreach/bulk-preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function submitFeedback(body: Record<string, unknown>) {
  const r = await fetch(`${base}/api/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
