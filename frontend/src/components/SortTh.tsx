import { memo } from "react";
import type { SortColumn } from "../atRiskTableUtils";

function SortThInner({
  col,
  label,
  sortColumn,
  sortDir,
  onSort,
}: {
  col: SortColumn;
  label: string;
  sortColumn: SortColumn;
  sortDir: "asc" | "desc";
  onSort: (c: SortColumn) => void;
}) {
  const active = sortColumn === col;
  const arrow = active ? (sortDir === "asc" ? " ↑" : " ↓") : "";
  return (
    <th
      scope="col"
      aria-sort={
        active ? (sortDir === "asc" ? "ascending" : "descending") : "none"
      }
    >
      <button
        type="button"
        className={`th-sort${active ? " th-sort--active" : ""}`}
        onClick={() => onSort(col)}
      >
        {label}
        <span className="th-sort-indicator" aria-hidden>
          {arrow}
        </span>
      </button>
    </th>
  );
}

export const SortTh = memo(SortThInner);
