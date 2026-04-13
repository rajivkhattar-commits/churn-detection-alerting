import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { AtRiskItem, UiCopy, VenueDetail } from "./api";
import {
  bulkPreviewOutreach,
  fetchAtRisk,
  fetchUiCopy,
  fetchVenue,
  refreshServerData,
  runScore,
} from "./api";
import {
  applyDocumentTheme,
  effectiveTheme,
  getStoredPreference,
  THEME_STORAGE_KEY,
  type ThemePreference,
} from "./theme";
import {
  compareGroupKeys,
  defaultSortDir,
  formatGroupLabel,
  GROUP_MODE_OPTIONS,
  type GroupMode,
  matchesFilters,
  rowGroupKey,
  type SortColumn,
  sortRows,
  uniqueVenueCount,
} from "./atRiskTableUtils";
import {
  DEV_CHURN_PREVIEW_EMAIL,
  FILTER_NONE,
  PRESETS,
  STRICT_PROD,
} from "./constants";
import { cutoffBandClass } from "./formatUtils";
import { AtRiskTableRow } from "./components/AtRiskTableRow";
import { FilteredTotalsRow } from "./components/FilteredTotalsRow";
import { HelpInstructions } from "./components/HelpInstructions";
import { SortTh } from "./components/SortTh";
import { VenueDetailPanel } from "./components/VenueDetailPanel";

export default function App() {
  const [items, setItems] = useState<AtRiskItem[]>([]);
  const [minRiskPercent, setMinRiskPercent] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [uiCopy, setUiCopy] = useState<UiCopy | null>(null);
  const [selected, setSelected] = useState<{
    venue_id: string;
    product: string;
  } | null>(null);
  const [detail, setDetail] = useState<VenueDetail | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [bulkOutreachResult, setBulkOutreachResult] = useState<string | null>(null);
  const [bulkOutreachLoading, setBulkOutreachLoading] = useState(false);
  const [sortColumn, setSortColumn] = useState<SortColumn>("churn");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filterProduct, setFilterProduct] = useState("");
  const [filterBrand, setFilterBrand] = useState("");
  const [filterCountry, setFilterCountry] = useState("");
  const [groupMode, setGroupMode] = useState<GroupMode>("brand_country");
  const [collapsedKeys, setCollapsedKeys] = useState<Set<string>>(() => new Set());
  const [themePreference, setThemePreference] = useState<ThemePreference>(() =>
    getStoredPreference()
  );
  const scoreMeaningDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    applyDocumentTheme(effectiveTheme(themePreference));
    try {
      localStorage.setItem(THEME_STORAGE_KEY, themePreference);
    } catch {
      /* ignore */
    }
  }, [themePreference]);

  useEffect(() => {
    if (themePreference !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const sync = () => applyDocumentTheme(effectiveTheme("system"));
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, [themePreference]);

  /** min_risk for API (0–1). Dev adds a fine-grained slider; production uses tier presets only. */
  const minRiskForApi = minRiskPercent / 100;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [list, copy] = await Promise.all([
        fetchAtRisk(minRiskForApi),
        fetchUiCopy(),
      ]);
      setItems(list);
      setUiCopy(copy);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [minRiskForApi]);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await refreshServerData();
      const [list, copy] = await Promise.all([
        fetchAtRisk(minRiskForApi),
        fetchUiCopy(),
      ]);
      setItems(list);
      setUiCopy(copy);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [minRiskForApi]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!selected || !modalOpen) {
      if (!modalOpen) setDetail(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const d = await fetchVenue(selected.venue_id, selected.product);
        if (!cancelled) setDetail(d);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected, modalOpen]);

  useEffect(() => {
    if (!modalOpen && !helpOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (helpOpen) {
        setHelpOpen(false);
        return;
      }
      setModalOpen(false);
      setSelected(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modalOpen, helpOpen]);

  const openRow = useCallback((row: AtRiskItem) => {
    setSelected({ venue_id: row.venue_id, product: row.product });
    setModalOpen(true);
  }, []);

  const onFeedbackError = useCallback((message: string) => {
    setError(message);
  }, []);

  const closeModal = () => {
    scoreMeaningDialogRef.current?.close();
    setModalOpen(false);
    setSelected(null);
  };

  const toggleSort = useCallback((col: SortColumn) => {
    if (col === sortColumn) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortColumn(col);
      setSortDir(defaultSortDir(col));
    }
  }, [sortColumn]);

  const filterOptions = useMemo(() => {
    const products = new Map<string, string>();
    const brands = new Set<string>();
    const countries = new Set<string>();
    for (const row of items) {
      products.set(row.product, row.product_display || row.product);
      if (row.brand_name) brands.add(row.brand_name);
      if (row.country_code) countries.add(row.country_code);
    }
    const productOpts = [...products.entries()]
      .sort((a, b) => a[1].localeCompare(b[1]))
      .map(([code, label]) => ({ code, label }));
    const brandOpts = [...brands].sort((a, b) => a.localeCompare(b));
    const countryOpts = [...countries].sort((a, b) => a.localeCompare(b));
    const hasNoBrand = items.some((r) => !r.brand_name);
    const hasNoCountry = items.some((r) => !r.country_code);
    return {
      products: productOpts,
      brands: brandOpts,
      countries: countryOpts,
      hasNoBrand,
      hasNoCountry,
    };
  }, [items]);

  const filteredRows = useMemo(
    () =>
      items.filter((row) =>
        matchesFilters(row, filterProduct, filterBrand, filterCountry)
      ),
    [items, filterProduct, filterBrand, filterCountry]
  );

  const groupedSections = useMemo(() => {
    if (groupMode === "flat") {
      const rows = sortRows(filteredRows, sortColumn, sortDir);
      return [
        {
          key: "__flat__",
          label: "",
          rows,
          venueCount: uniqueVenueCount(rows),
          groupHeaderTitle: undefined,
        },
      ];
    }
    const byKey = new Map<string, AtRiskItem[]>();
    for (const row of filteredRows) {
      const k = rowGroupKey(row, groupMode);
      if (!byKey.has(k)) byKey.set(k, []);
      byKey.get(k)!.push(row);
    }
    const keys = [...byKey.keys()].sort((a, b) =>
      compareGroupKeys(a, b, groupMode)
    );
    return keys.map((k) => {
      const groupRows = byKey.get(k)!;
      const sorted = sortRows(groupRows, sortColumn, sortDir);
      const sample = groupRows[0];
      return {
        key: k,
        label: formatGroupLabel(k, groupMode, sample),
        rows: sorted,
        venueCount: uniqueVenueCount(groupRows),
        groupHeaderTitle:
          groupMode === "venue_id" ? `Venue ID: ${k}` : undefined,
      };
    });
  }, [filteredRows, sortColumn, sortDir, groupMode]);

  useEffect(() => {
    setCollapsedKeys(new Set());
  }, [groupMode]);

  const toggleGroupCollapsed = useCallback((key: string) => {
    setCollapsedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const expandAllGroups = useCallback(() => {
    setCollapsedKeys(new Set());
  }, []);

  const collapseAllGroups = useCallback(() => {
    if (groupMode === "flat") return;
    setCollapsedKeys(new Set(groupedSections.map((s) => s.key)));
  }, [groupMode, groupedSections]);

  const totals = useMemo(() => {
    const rowCount = filteredRows.length;
    const venueIds = new Set(filteredRows.map((r) => r.venue_id));
    return { rowCount, uniqueVenues: venueIds.size };
  }, [filteredRows]);

  return (
    <>
      <div className="app-theme-bar">
        <button
          type="button"
          className="app-help-trigger"
          onClick={() => setHelpOpen(true)}
          aria-haspopup="dialog"
          aria-expanded={helpOpen}
          aria-controls="help-dialog"
        >
          How this works
        </button>
        <div className="app-theme-bar-spacer" aria-hidden />
        <label htmlFor="theme-select" className="app-theme-label">
          Appearance
        </label>
        <select
          id="theme-select"
          className="app-theme-select"
          value={themePreference}
          onChange={(e) =>
            setThemePreference(e.target.value as ThemePreference)
          }
          aria-label="Color theme"
        >
          <option value="dark">Night</option>
          <option value="light">Day</option>
          <option value="system">System</option>
        </select>
      </div>
      <div className="layout layout--wide">
      <header className="header">
        <h1>Enterprise venue churn</h1>
        <p className="muted">
          Churn likelihood is a 0–100% estimate per venue × product surface — validate in
          Snowflake and with your ENT playbooks.
        </p>
        {uiCopy && (
          <details className="header-score-meaning">
            <summary className="header-score-meaning-summary">
              What the risk score means
            </summary>
            <p className="muted small header-score-meaning-body">{uiCopy.score_meaning}</p>
          </details>
        )}
      </header>

      <section className="toolbar toolbar--filter">
        <div className="filter-block filter-block--pipeline">
          <div className="filter-label">
            <strong>Focus your pipeline</strong>
            <span className="filter-hint">
              {STRICT_PROD ? (
                <>
                  Only venues at or above this churn likelihood are listed (aligned with category
                  bands). Use <strong>All accounts</strong> for the full at-risk set. The fine-tune
                  slider is available in non-strict builds only.
                </>
              ) : (
                <>
                  Use a <strong>churn likelihood cutoff</strong> for this view. Only venues at or
                  above that likelihood appear in the table (same score as the &quot;Churn
                  likelihood&quot; column). <strong>Risk tier</strong> presets are available in every
                  build.
                </>
              )}
            </span>
          </div>
          <div className="filter-presets-block">
            <p className="filter-subheading" id="pipeline-tier-presets-label">
              Risk tiers
            </p>
            <div
              className="presets presets--pipeline-tiers"
              role="group"
              aria-labelledby="pipeline-tier-presets-label"
              aria-label="Risk level presets"
            >
              {PRESETS.map((p) => (
                <button
                  key={p.label}
                  type="button"
                  className={
                    minRiskPercent === p.percent
                      ? `preset active preset--${p.band}`
                      : `preset preset--${p.band}`
                  }
                  onClick={() => setMinRiskPercent(p.percent)}
                >
                  {p.label}
                  <span className="preset-sub">{p.percent}%</span>
                </button>
              ))}
            </div>
          </div>
          {!STRICT_PROD && (
            <div
              className="filter-dev-slider-panel"
              aria-label="Dev-only fine-tune churn likelihood cutoff"
            >
              <div className="filter-dev-slider-panel-header">
                <span className="filter-dev-slider-panel-title">Fine-tune cutoff</span>
                <span className="dev-only-badge dev-only-badge--inline">Dev only</span>
              </div>
              <p className="filter-slider-caption filter-dev-slider-intro">
                Drag between 0–100% (5% steps) for thresholds that don&apos;t match a tier button.
              </p>
              <div className="filter-slider-section">
                <div className="filter-cutoff-line" id="cutoff-summary">
                  <span
                    className={`filter-cutoff-value ${cutoffBandClass(minRiskPercent)}`}
                  >
                    {minRiskPercent}%
                  </span>
                  <span className="filter-cutoff-desc">
                    cutoff — minimum churn likelihood to include in this analysis
                  </span>
                </div>
                <div
                  className="filter-slider-row"
                  role="group"
                  aria-labelledby="cutoff-summary"
                  aria-describedby="cutoff-caption"
                >
                  <span
                    className="filter-slider-end filter-slider-end--low"
                    id="slider-low"
                  >
                    Low risk
                  </span>
                  <input
                    type="range"
                    className="filter-range filter-range--dev"
                    min={0}
                    max={100}
                    step={5}
                    value={minRiskPercent}
                    onChange={(e) => setMinRiskPercent(Number(e.target.value))}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={minRiskPercent}
                    aria-label="Dev only: churn likelihood cutoff for the account list"
                  />
                  <span
                    className="filter-slider-end filter-slider-end--high"
                    id="slider-high"
                  >
                    High risk
                  </span>
                </div>
                <p className="filter-slider-caption" id="cutoff-caption">
                  This threshold only filters the list — it does not change how likelihood is
                  calculated.
                </p>
              </div>
            </div>
          )}
        </div>
        <div className="toolbar-actions">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={loading}
            title="Reload data files on the server, re-score all venues, then update this table"
          >
            Refresh
          </button>
          <div
            className="toolbar-dev-action"
            title={
              STRICT_PROD
                ? "Re-score is disabled in strict production UI (VITE_STRICT_PROD=true at build)."
                : "Re-run the model on snapshots already in memory (does not reload JSON files)"
            }
          >
            <span className="dev-only-badge dev-only-badge--toolbar">Dev only</span>
            <button
              type="button"
              className="toolbar-rescore-btn"
              disabled={loading || STRICT_PROD}
              aria-label={
                STRICT_PROD
                  ? "Re-score only (no reload) — disabled when built with VITE_STRICT_PROD=true"
                  : "Re-score only (no reload)"
              }
              onClick={async () => {
                setError(null);
                try {
                  await runScore();
                  await load();
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              Re-score only (no reload)
            </button>
          </div>
          {!STRICT_PROD && (
            <div
              className="toolbar-dev-action"
              title="Dry run: 1 summary email + 1 Slack digest (production would send one email and one Slack per surface)"
            >
              <span className="dev-only-badge dev-only-badge--toolbar">Dev only</span>
              <button
                type="button"
                className="toolbar-churn-preview-btn"
                disabled={loading || bulkOutreachLoading || filteredRows.length === 0}
                onClick={async () => {
                  setBulkOutreachResult(null);
                  setError(null);
                  setBulkOutreachLoading(true);
                  try {
                    const res = await bulkPreviewOutreach({
                      preview_to_email: DEV_CHURN_PREVIEW_EMAIL,
                      template_id: "am_churn_alert",
                      rows: filteredRows.map((r) => ({
                        venue_id: r.venue_id,
                        product: r.product,
                        market: r.market,
                        country_code: r.country_code,
                      })),
                    });
                    setBulkOutreachResult(JSON.stringify(res, null, 2));
                  } catch (e) {
                    setError(String(e));
                  } finally {
                    setBulkOutreachLoading(false);
                  }
                }}
              >
                {bulkOutreachLoading
                  ? "Sending dry run…"
                  : "Dry run (1 email + 1 Slack)"}
              </button>
            </div>
          )}
        </div>
      </section>

      {error && <div className="error">{error}</div>}
      {!STRICT_PROD && bulkOutreachResult && (
        <pre className="json small bulk-outreach-result" aria-label="Outreach dry run API response">
          {bulkOutreachResult}
        </pre>
      )}

      <section className="at-risk-shell">
        <h2 className="at-risk-title">At risk</h2>
        <p className="muted small table-legend">
          <strong>Total (filtered)</strong> at the top and bottom shows venue and row counts for your
          filters. Each group header includes a <strong>Subtotal</strong> (unique venues · rows in that
          group). Use <strong>Group by</strong> to cluster rows; <strong>▼</strong> collapses a section.
          Column sort is within each group unless you use <strong>Flat list</strong>.
          {!STRICT_PROD && (
            <>
              {" "}
              Brand / geo from <code>venue_enrichment.json</code>; production: join{" "}
              <code>venue_id</code> to merchant / <code>d_merchant_tier</code> in Snowflake.
            </>
          )}
        </p>
        {loading ? (
          <p>Loading…</p>
        ) : (
          <>
            <div className="table-filters" aria-label="Table filters">
              <div className="table-filters-band">
                <span className="table-filters-band-label">View</span>
                <div className="table-filters-band-controls table-filters-band-controls--view">
                  <div className="table-filter-field table-filter-field--groupby">
                    <label htmlFor="group-mode">Group by</label>
                    <select
                      id="group-mode"
                      value={groupMode}
                      onChange={(e) => setGroupMode(e.target.value as GroupMode)}
                    >
                      {GROUP_MODE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  {groupMode !== "flat" && totals.rowCount > 0 && (
                    <div
                      className="table-group-actions"
                      role="group"
                      aria-label="Group expand and collapse"
                    >
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={expandAllGroups}
                      >
                        Expand all
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={collapseAllGroups}
                      >
                        Collapse all
                      </button>
                    </div>
                  )}
                </div>
              </div>
              <div className="table-filters-band">
                <span className="table-filters-band-label">Refine</span>
                <div className="table-filters-band-controls">
                  <div className="table-filter-field">
                    <label htmlFor="filter-product">Product</label>
                    <select
                      id="filter-product"
                      value={filterProduct}
                      onChange={(e) => setFilterProduct(e.target.value)}
                    >
                      <option value="">All products</option>
                      {filterOptions.products.map((p) => (
                        <option key={p.code} value={p.code}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="table-filter-field">
                    <label htmlFor="filter-brand">Brand</label>
                    <select
                      id="filter-brand"
                      value={filterBrand}
                      onChange={(e) => setFilterBrand(e.target.value)}
                    >
                      <option value="">All brands</option>
                      {filterOptions.hasNoBrand && (
                        <option value={FILTER_NONE}>— (no brand)</option>
                      )}
                      {filterOptions.brands.map((b) => (
                        <option key={b} value={b}>
                          {b}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="table-filter-field">
                    <label htmlFor="filter-country">Country</label>
                    <select
                      id="filter-country"
                      value={filterCountry}
                      onChange={(e) => setFilterCountry(e.target.value)}
                    >
                      <option value="">All countries</option>
                      {filterOptions.hasNoCountry && (
                        <option value={FILTER_NONE}>— (no code)</option>
                      )}
                      {filterOptions.countries.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            </div>
            <div className="table-scroll">
              <table className="table table--at-risk">
                <thead>
                  <tr>
                    <SortTh
                      col="brand"
                      label="Brand"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                    <SortTh
                      col="country"
                      label="Country"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                    <SortTh
                      col="city"
                      label="City"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                    <SortTh
                      col="venue_id"
                      label="Venue ID"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                    <SortTh
                      col="volume"
                      label="Volume (L90D)"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                    <SortTh
                      col="product"
                      label="Product"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                    <SortTh
                      col="churn"
                      label="Churn likelihood"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                    <SortTh
                      col="category"
                      label="Category"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                    <SortTh
                      col="hypothesis"
                      label="AI hypothesis"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                    <SortTh
                      col="driver"
                      label="Churn driver"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                    <SortTh
                      col="tips"
                      label="Further exploration"
                      sortColumn={sortColumn}
                      sortDir={sortDir}
                      onSort={toggleSort}
                    />
                  </tr>
                </thead>
                <tbody>
                  {totals.rowCount === 0 ? (
                    <tr>
                      <td colSpan={11} className="table-empty">
                        No rows match the current filters (or the list is empty).
                      </td>
                    </tr>
                  ) : (
                    <>
                      <FilteredTotalsRow
                        position="top"
                        uniqueVenues={totals.uniqueVenues}
                        rowCount={totals.rowCount}
                      />
                      {groupedSections.flatMap((section) => {
                        const isFlat = groupMode === "flat";
                        const collapsed =
                          !isFlat && collapsedKeys.has(section.key);
                        const dataRows = section.rows.map((row) => (
                          <AtRiskTableRow
                            key={`${row.venue_id}-${row.product}`}
                            row={row}
                            onOpen={openRow}
                          />
                        ));
                        if (isFlat) {
                          return dataRows;
                        }
                        const header = (
                          <tr key={`g-${section.key}`} className="table-group-row">
                            <td colSpan={11} className="table-group-cell">
                              <button
                                type="button"
                                className="table-group-toggle"
                                onClick={() => toggleGroupCollapsed(section.key)}
                                aria-expanded={!collapsed}
                                title={section.groupHeaderTitle}
                              >
                                <span className="table-group-chevron" aria-hidden>
                                  {collapsed ? "▶" : "▼"}
                                </span>
                                <span className="table-group-cluster">
                                  <span className="table-group-title">{section.label}</span>
                                  <span className="table-group-subtotal">
                                    Subtotal: {section.venueCount} venue
                                    {section.venueCount === 1 ? "" : "s"} ·{" "}
                                    {section.rows.length} row
                                    {section.rows.length === 1 ? "" : "s"}
                                  </span>
                                </span>
                              </button>
                            </td>
                          </tr>
                        );
                        return collapsed ? [header] : [header, ...dataRows];
                      })}
                    </>
                  )}
                </tbody>
                {totals.rowCount > 0 && (
                  <tfoot>
                    <FilteredTotalsRow
                      position="bottom"
                      uniqueVenues={totals.uniqueVenues}
                      rowCount={totals.rowCount}
                    />
                  </tfoot>
                )}
              </table>
            </div>
          </>
        )}
      </section>

      {helpOpen && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) setHelpOpen(false);
          }}
        >
          <div
            id="help-dialog"
            className="modal-panel modal-panel--help"
            role="dialog"
            aria-modal="true"
            aria-labelledby="help-title"
          >
            <div className="modal-header">
              <h2 id="help-title">How this works</h2>
              <button
                type="button"
                className="modal-close"
                onClick={() => setHelpOpen(false)}
                aria-label="Close instructions"
              >
                ×
              </button>
            </div>
            <div className="modal-body help-body">
              <HelpInstructions strictProd={STRICT_PROD} />
            </div>
          </div>
        </div>
      )}

      {modalOpen && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeModal();
          }}
        >
          <div
            className="modal-panel modal-panel--detail"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <div className="modal-header">
              <h2 id="modal-title">Venue detail</h2>
              <button
                type="button"
                className="modal-close"
                onClick={closeModal}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            {selected && !detail && (
              <div className="modal-body detail-modal-body">
                <p className="muted">Loading…</p>
              </div>
            )}
            {selected && detail && (
              <VenueDetailPanel
                detail={detail}
                selectedVenueId={selected.venue_id}
                selectedProduct={selected.product}
                strictProd={STRICT_PROD}
                scoreMeaningDialogRef={scoreMeaningDialogRef}
                onFeedbackError={onFeedbackError}
              />
            )}
          </div>
        </div>
      )}
    </div>
    </>
  );
}
