import { memo } from "react";
import type { AtRiskItem } from "../api";
import { formatL90dOrders, formatPct } from "../formatUtils";
import { BandFlag } from "./BandFlag";

function AtRiskTableRowInner({
  row,
  onOpen,
}: {
  row: AtRiskItem;
  onOpen: (row: AtRiskItem) => void;
}) {
  const volumeTitle =
    row.orders_90d != null
      ? `${formatL90dOrders(row.orders_90d)} orders (L90D)${
          row.volume_segment_label ? ` · ${row.volume_segment_label}` : ""
        }`
      : row.volume_segment_label || "";

  return (
    <tr className="click-row" onClick={() => onOpen(row)}>
      <td className="nowrap">{row.brand_name ?? "—"}</td>
      <td className="nowrap">{row.country_code ?? "—"}</td>
      <td className="nowrap">{row.city ?? row.market ?? "—"}</td>
      <td className="mono tiny venue-id-cell" title={row.venue_id}>
        {row.venue_id}
      </td>
      <td className="nowrap volume-cell" title={volumeTitle}>
        {row.orders_90d != null
          ? formatL90dOrders(row.orders_90d)
          : row.volume_segment_label || "—"}
      </td>
      <td>{row.product_display || row.product}</td>
      <td className="nowrap strong">{formatPct(row.churn_likelihood)}</td>
      <td>
        <BandFlag label={row.risk_band_label} bandKey={row.risk_band_key} />
      </td>
      <td className="hypothesis-cell">{row.ai_hypothesis ?? "—"}</td>
      <td className="driver-cell" title={row.churn_reason_summary}>
        {row.churn_reason_summary || "—"}
      </td>
      <td className="tips-cell" title={row.exploration_tips}>
        {row.exploration_tips}
      </td>
    </tr>
  );
}

/** Skips re-render when parent re-renders but this row’s data and handler are unchanged. */
export const AtRiskTableRow = memo(AtRiskTableRowInner);
