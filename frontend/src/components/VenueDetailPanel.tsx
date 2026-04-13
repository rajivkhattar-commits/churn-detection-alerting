import { memo, useCallback, useMemo, type MutableRefObject } from "react";
import type { VenueDetail } from "../api";
import { submitFeedback } from "../api";
import {
  ASKWOLTAI_MCP_GITHUB_HREF,
  DEV_CHURN_PREVIEW_EMAIL,
} from "../constants";
import {
  CHURN_STYLE_SALES,
  CHURN_STYLE_SHORT,
  churnStyleSorted,
} from "../churnStyle";
import { formatL90dOrders, formatPct, shortId } from "../formatUtils";
import { BandFlag } from "./BandFlag";

function VenueDetailPanelInner({
  detail,
  selectedVenueId,
  selectedProduct,
  strictProd,
  scoreMeaningDialogRef,
  onFeedbackError,
}: {
  detail: VenueDetail;
  selectedVenueId: string;
  selectedProduct: string;
  strictProd: boolean;
  scoreMeaningDialogRef: MutableRefObject<HTMLDialogElement | null>;
  onFeedbackError: (message: string) => void;
}) {
  const churnSorted = useMemo(
    () =>
      churnStyleSorted(
        detail.latest.churn_type_probs as Record<string, unknown> | undefined
      ),
    [detail.latest.churn_type_probs]
  );
  const churnTop = churnSorted[0];
  const churnSecond = churnSorted[1];
  const churnCopy = churnTop ? CHURN_STYLE_SALES[churnTop.key] : null;
  const showChurnRunner =
    churnTop != null &&
    churnSecond != null &&
    churnSecond.p >= 0.18 &&
    churnSecond.key !== churnTop.key;

  const onFeedbackClick = useCallback(async () => {
    const runId = detail.latest?.run_id;
    if (!runId) return;
    try {
      await submitFeedback({
        cohort: {
          venue_id: selectedVenueId,
          merchant_id: null,
          market: detail.market,
          country_code: detail.country_code,
        },
        product: selectedProduct,
        run_id: runId,
        hypothesis_index: 0,
        rating: "partial",
        comment: "UI smoke test",
      });
      alert("Feedback recorded");
    } catch (e) {
      onFeedbackError(String(e));
    }
  }, [detail, selectedVenueId, selectedProduct, onFeedbackError]);

  return (
    <div className="modal-body detail-modal-body">
      <section className="detail-card">
        <h3 className="detail-brand-title">
          {detail.brand_name ?? detail.venue_display_name ?? shortId(detail.venue_id)}
        </h3>
        <dl className="detail-hero-meta">
          <div className="detail-hero-row">
            <dt>Country</dt>
            <dd>
              {detail.country_code ?? "—"}
              {detail.city || detail.market ? ` · ${detail.city ?? detail.market}` : ""}
            </dd>
          </div>
          <div className="detail-hero-row">
            <dt>Product</dt>
            <dd>{detail.product_display}</dd>
          </div>
          <div className="detail-hero-row">
            <dt>Venue ID</dt>
            <dd>
              <span className="mono detail-hero-venue-id">{detail.venue_id}</span>
            </dd>
          </div>
        </dl>

        <div className="score-block score-block--hero">
          <div className="score-main score-main--with-info">
            <span className="score-num">{formatPct(detail.latest.risk_score)}</span>
            <span className="muted">churn likelihood</span>
            <button
              type="button"
              className="score-meaning-info-btn"
              aria-label="What the score means — opens a short dialog"
              title="What the score means"
              onClick={() => scoreMeaningDialogRef.current?.showModal()}
            >
              ⓘ
            </button>
            <BandFlag label={detail.risk_band_label} bandKey={detail.risk_band_key} />
          </div>
        </div>

        <dialog
          ref={scoreMeaningDialogRef}
          className="score-meaning-dialog"
          aria-labelledby="score-meaning-dialog-title"
        >
          <div className="score-meaning-dialog-panel">
            <div className="score-meaning-dialog-header">
              <h4 id="score-meaning-dialog-title">What the score means</h4>
              <button
                type="button"
                className="modal-close score-meaning-dialog-close"
                onClick={() => scoreMeaningDialogRef.current?.close()}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <p className="small score-meaning-dialog-text">{detail.score_meaning}</p>
          </div>
        </dialog>

        <div className="detail-signals">
          <h4 className="detail-signals-title">Why this churn likelihood</h4>
          <p className="detail-signals-intro small muted">
            These signals inform the rating above — hypotheses to validate in Snowflake and with your
            playbook, not a finance verdict.
          </p>
          <div className="detail-signal-block">
            <div className="detail-signal-label">
              {strictProd ? "Primary churn driver" : "Churn driver (demo narrative)"}
            </div>
            <p className="detail-signal-text small">{detail.churn_reason_summary || "—"}</p>
          </div>
          <div className="detail-signal-block">
            <div className="detail-signal-label">Risk band</div>
            <p className="detail-signal-text small">{detail.risk_band_detail}</p>
          </div>
          <div className="detail-signal-block">
            <div className="detail-signal-label">Volume (L90D)</div>
            <p className="detail-signal-text small">
              {detail.orders_90d != null ? formatL90dOrders(detail.orders_90d) : "—"}
              {detail.volume_segment_label ? (
                <span className="muted"> ({detail.volume_segment_label})</span>
              ) : null}
            </p>
          </div>
          <div className="detail-signal-block">
            <div className="detail-signal-label">Exploration</div>
            <p className="detail-signal-text small">{detail.exploration_tips}</p>
          </div>
        </div>

        <div className="churn-style-sales">
          <h4>What to explore first</h4>
          {churnSorted.length === 0 || !churnCopy ? (
            <p className="small muted">No angle breakdown for this row.</p>
          ) : (
            <>
              <p className="churn-style-sales-lead">{churnCopy.lead}</p>
              <p className="small">{churnCopy.detail}</p>
              {showChurnRunner && churnSecond ? (
                <p className="small muted">
                  Also in the mix: <strong>{CHURN_STYLE_SHORT[churnSecond.key]}</strong>.
                  {!strictProd ? (
                    <>
                      {" "}
                      Percentages are listed under <em>Model mix &amp; percentages (dev only)</em> below.
                    </>
                  ) : null}
                </p>
              ) : null}
              {strictProd ? (
                <p className="small muted churn-style-sales-note">
                  This is a rough blend of signals (not a finance label). Use it as a conversation guide
                  and validate in Snowflake with your ENT playbook.
                </p>
              ) : null}
            </>
          )}
          <p className="small detail-askwolt-cta">
            <a href={ASKWOLTAI_MCP_GITHUB_HREF} target="_blank" rel="noopener noreferrer">
              AskWoltAI MCP on GitHub
            </a>{" "}
            — install the MCP in Cursor, connect Snowflake, and explore venue / merchant data
            yourself (same <code>schema.py</code> alignment as this service).
          </p>
          {!strictProd && (
            <details className="churn-style-dev-details">
              <summary>Model mix &amp; percentages (dev only)</summary>
              <p className="small muted churn-dev-mix-note">
                Percentages below are heuristic model weights — not shown in strict production UI.
              </p>
              <ul className="mix">
                {churnSorted.map(({ key, p }) => (
                  <li key={key}>
                    <strong>{key}</strong>: {formatPct(p)}
                  </li>
                ))}
              </ul>
              <p className="small muted">{detail.churn_type_help}</p>
            </details>
          )}
        </div>
      </section>

      {!strictProd && detail.explanation && (
        <details>
          <summary>Raw explanation (JSON)</summary>
          <pre className="json small">{JSON.stringify(detail.explanation, null, 2)}</pre>
        </details>
      )}

      <div className="actions venue-detail-actions">
        {strictProd ? (
          <p className="small muted venue-outreach-note">
            Bulk account-manager alerts are not sent from this screen row-by-row. Use exports, CRM, or
            automated jobs that call the outreach API with routing data — not repeated clicks here.
          </p>
        ) : (
          <p className="small muted venue-outreach-note">
            <span className="dev-only-badge">Dev only</span> Use{" "}
            <strong>Dry run (1 email + 1 Slack)</strong> on the main toolbar: one summary email to{" "}
            <span className="mono">{DEV_CHURN_PREVIEW_EMAIL}</span> and one Slack digest, with
            venue/brand/product inventory and production send counts. Does not contact the real account
            manager.
          </p>
        )}
        {!strictProd && (
          <button type="button" onClick={onFeedbackClick}>
            Send sample feedback
          </button>
        )}
      </div>
    </div>
  );
}

export const VenueDetailPanel = memo(VenueDetailPanelInner);
