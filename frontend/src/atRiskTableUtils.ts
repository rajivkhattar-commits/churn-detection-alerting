import type { AtRiskItem } from "./api";
import { BAND_ORDER, FILTER_NONE } from "./constants";
import { shortId } from "./formatUtils";

export type SortColumn =
  | "brand"
  | "country"
  | "city"
  | "venue_id"
  | "volume"
  | "product"
  | "churn"
  | "category"
  | "hypothesis"
  | "driver"
  | "tips";

export type GroupMode =
  | "flat"
  | "brand_country"
  | "brand"
  | "country"
  | "venue_id"
  | "volume"
  | "product";

export const GROUP_MODE_OPTIONS: { value: GroupMode; label: string }[] = [
  { value: "flat", label: "Flat list (no grouping)" },
  { value: "brand_country", label: "Brand + country" },
  { value: "brand", label: "Brand only" },
  { value: "country", label: "Country only" },
  { value: "venue_id", label: "Venue ID" },
  { value: "volume", label: "Volume segment" },
  { value: "product", label: "Product surface" },
];

export function sortRows(
  rows: AtRiskItem[],
  col: SortColumn,
  dir: "asc" | "desc"
): AtRiskItem[] {
  const m = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    let c = 0;
    switch (col) {
      case "brand":
        c = (a.brand_name ?? "").localeCompare(b.brand_name ?? "");
        break;
      case "country":
        c = (a.country_code ?? "").localeCompare(b.country_code ?? "");
        break;
      case "city":
        c = (a.city ?? a.market ?? "").localeCompare(b.city ?? b.market ?? "");
        break;
      case "venue_id":
        c = a.venue_id.localeCompare(b.venue_id);
        break;
      case "volume": {
        const ao = a.orders_90d ?? -1;
        const bo = b.orders_90d ?? -1;
        c = ao - bo;
        break;
      }
      case "product":
        c = (a.product_display || a.product).localeCompare(b.product_display || b.product);
        break;
      case "churn":
        c = a.churn_likelihood - b.churn_likelihood;
        break;
      case "category":
        c = (BAND_ORDER[a.risk_band_key] ?? 0) - (BAND_ORDER[b.risk_band_key] ?? 0);
        break;
      case "hypothesis":
        c = (a.ai_hypothesis ?? "").localeCompare(b.ai_hypothesis ?? "");
        break;
      case "driver":
        c = (a.churn_reason_summary ?? "").localeCompare(b.churn_reason_summary ?? "");
        break;
      case "tips":
        c = (a.exploration_tips ?? "").localeCompare(b.exploration_tips ?? "");
        break;
      default:
        break;
    }
    if (c !== 0) return c * m;
    const v = a.venue_id.localeCompare(b.venue_id);
    if (v !== 0) return v;
    return a.product.localeCompare(b.product);
  });
}

export function rowGroupKey(row: AtRiskItem, mode: GroupMode): string {
  switch (mode) {
    case "flat":
      return "";
    case "brand_country":
      return `${row.brand_name ?? "—"}\t${row.country_code ?? "—"}`;
    case "brand":
      return row.brand_name ?? "—";
    case "country":
      return row.country_code ?? "—";
    case "venue_id":
      return row.venue_id;
    case "volume":
      return row.volume_segment ?? "—";
    case "product":
      return row.product;
    default:
      return "";
  }
}

export function compareGroupKeys(a: string, b: string, mode: GroupMode): number {
  if (mode === "volume") {
    const ord = (k: string) =>
      k === "high_volume_ent" ? 0 : k === "low_volume_ent" ? 1 : 99;
    const d = ord(a) - ord(b);
    if (d !== 0) return d;
  }
  if (mode === "brand_country") {
    const [ba, ca] = a.split("\t");
    const [bb, cb] = b.split("\t");
    const c1 = ba.localeCompare(bb);
    if (c1 !== 0) return c1;
    return ca.localeCompare(cb);
  }
  return a.localeCompare(b);
}

export function formatGroupLabel(key: string, mode: GroupMode, sample: AtRiskItem): string {
  switch (mode) {
    case "brand_country": {
      const [b, c] = key.split("\t");
      return `${b} · ${c}`;
    }
    case "brand":
      return key;
    case "country":
      return key;
    case "venue_id":
      return `${shortId(key)} · ${sample.brand_name ?? "—"} · ${sample.country_code ?? "—"}`;
    case "volume":
      return sample.volume_segment_label || key;
    case "product":
      return sample.product_display || sample.product;
    default:
      return key;
  }
}

export function matchesFilters(
  row: AtRiskItem,
  product: string,
  brand: string,
  country: string
): boolean {
  if (product && row.product !== product) return false;
  if (brand) {
    const b = row.brand_name ?? "";
    if (brand === FILTER_NONE) {
      if (b !== "") return false;
    } else if (b !== brand) return false;
  }
  if (country) {
    const cc = row.country_code ?? "";
    if (country === FILTER_NONE) {
      if (cc !== "") return false;
    } else if (cc !== country) return false;
  }
  return true;
}

export function defaultSortDir(col: SortColumn): "asc" | "desc" {
  if (col === "churn" || col === "category" || col === "volume") return "desc";
  return "asc";
}

export function uniqueVenueCount(rows: AtRiskItem[]): number {
  return new Set(rows.map((r) => r.venue_id)).size;
}
