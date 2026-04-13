export function FilteredTotalsRow({
  position,
  uniqueVenues,
  rowCount,
}: {
  position: "top" | "bottom";
  uniqueVenues: number;
  rowCount: number;
}) {
  const isTop = position === "top";
  return (
    <tr
      className={`table-totals-row table-totals-row--${position}`}
      aria-label={
        isTop
          ? "Filtered totals — scope of current filters"
          : "Filtered totals — repeated at bottom"
      }
    >
      <td className="table-totals-label" colSpan={3}>
        Total (filtered)
      </td>
      <td className="table-totals-values" colSpan={8}>
        <strong>{uniqueVenues}</strong> unique venues · <strong>{rowCount}</strong> rows{" "}
        <span className="muted table-totals-hint">(venue × product surfaces)</span>
      </td>
    </tr>
  );
}
