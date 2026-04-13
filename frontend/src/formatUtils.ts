/** Display helpers shared across the at-risk table and venue detail. */

export function formatPct(x: number): string {
  return `${(x * 100).toFixed(1)}%`;
}

/** Last-90-days order count (venue-level); matches pipeline / demo CSV `orders_90d`. */
export function formatL90dOrders(n: number | null | undefined): string {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return Math.round(Number(n)).toLocaleString();
}

export function shortId(id: string): string {
  if (id.length <= 20) return id;
  return `${id.slice(0, 10)}…${id.slice(-6)}`;
}

export function cutoffBandClass(pct: number): string {
  if (pct >= 75) return "filter-cutoff-value--critical";
  if (pct >= 55) return "filter-cutoff-value--high_priority";
  if (pct >= 35) return "filter-cutoff-value--elevated";
  return "filter-cutoff-value--lower_concern";
}
