import { memo } from "react";

function HelpInstructionsInner({ strictProd }: { strictProd: boolean }) {
  return (
    <div className="help-layout">
      <section
        className="help-group help-group--production"
        aria-labelledby="help-group-production-title"
      >
        <header className="help-group-header">
          <h3 id="help-group-production-title" className="help-group-title">
            Production
          </h3>
          <p className="help-group-intro">
            Included in release builds — this is the surface you can expect long term.
          </p>
        </header>
        <div className="help-group-body">
          <section className="help-section">
            <h4 className="help-section-title">This page</h4>
            <p>
              A prioritized list of Enterprise venues by product surface, with churn likelihood and
              supporting context. Use it alongside Snowflake and your internal playbooks — not as a
              sole source of truth.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">How the churn likelihood is calculated</h4>
            <p>
              The percentage is a <strong>calibrated probability</strong> from a{" "}
              <strong>logistic regression</strong> model: we take recent numeric signals for each
              venue × product, scale them consistently, then the model outputs a score between 0% and
              100%. Calibration means the number is tuned so it reads like a sensible &quot;how
              worried should we be&quot; dial for prioritization — not a guarantee that a venue will
              leave.
            </p>
            <p>
              The model learns its <strong>weights from historical examples</strong> (churn-like
              outcomes vs not). After each retrain, the strongest predictors can shift slightly; there
              is no fixed manual rule like &quot;always 40% orders.&quot; In practice, the signals
              below are what the math sees; <strong>falling demand</strong> (orders and sales trends),{" "}
              <strong>weak performance vs similar venues</strong>, and{" "}
              <strong>operational friction</strong> (support load, integration issues, opening hours)
              are the story the model is built to pick up.
            </p>
            <p>Inputs (all rolled into that one score):</p>
            <ul className="help-list">
              <li>
                <strong>Demand and revenue</strong> — order volume (7 and 28 days), sales (GMV) in
                the last month, week-over-week order change, month-over-month sales change, and where
                the venue sits vs peers (peer GMV percentile).
              </li>
              <li>
                <strong>Engagement</strong> — how often the partner used key tools in the last month
                (login days).
              </li>
              <li>
                <strong>Friction and operations</strong> — support tickets, integration/config error
                rates, menu or catalog sync failures, and days with zero opening hours (open hours
                missing or closed).
              </li>
            </ul>
            <p>
              <strong>Churn &quot;category&quot;</strong> (soft vs hard vs operational) in the table
              and detail is a separate, lighter blend on top of the same signals — useful for talk
              tracks, not a second independent forecast.
            </p>
            <p>
              If a trained model file is not deployed in a given environment, the service falls back to
              a simple rule-based score using the same inputs so lists still rank sensibly for demos.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">Refresh</h4>
            <p>
              Asks the server to reload venue feature data and enrichment, then{" "}
              <strong>re-run churn scoring</strong> for every row, and finally reloads this table. In
              production, upstream data is usually refreshed on a <strong>daily schedule</strong>{" "}
              (batch / warehouse job); use Refresh after that job has written new materialized data to
              the server, or when you need this service to pick up updated files without restarting it.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">Table</h4>
            <p>
              <strong>Group by</strong> clusters rows (for example by brand and country, or by venue
              ID). <strong>Product / Brand / Country</strong> narrow the list. Preset tiers (and the
              optional fine-tune slider when not in strict mode) set the minimum churn likelihood for
              rows loaded from the API; <strong>All accounts</strong> uses <code>min_risk=0</code> for
              the full cohort. Column headers sort rows (within each group unless you use a flat list).{" "}
              <strong>Total (filtered)</strong> and per-group <strong>Subtotal</strong> counts reflect
              what is visible after filters.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">Venue detail</h4>
            <p>
              Open a row for brand, country, product, venue ID, then churn likelihood. Use the{" "}
              <strong>ⓘ</strong> button next to the score to read <strong>What the score means</strong>{" "}
              in a small dialog (no long copy inline). <strong>Why this churn likelihood</strong> groups
              drivers, band, volume, and exploration so you can see what fed the rating.{" "}
              <strong>What to explore first</strong> includes a link to the AskWoltAI MCP GitHub repo.
              Unless the UI was built with <code>VITE_STRICT_PROD=true</code>, expand{" "}
              <strong>Model mix &amp; percentages (dev only)</strong> for heuristic soft/hard/
              operational weights.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">Churn alerts (account managers)</h4>
            <p>
              Automated or integrated jobs can send real email to the <strong>account manager</strong>{" "}
              using routing data (for example <code>data/am_assignments.json</code> or a warehouse
              export). The venue detail screen in strict UI does not offer row-by-row AM blast — use
              exports and playbooks for bulk outreach. Outbound email requires SMTP on the server.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">Appearance</h4>
            <p>
              <strong>Night</strong> and <strong>Day</strong> fix the theme. <strong>System</strong>{" "}
              follows your OS light/dark preference.
            </p>
          </section>
        </div>
      </section>

      <section
        className="help-group help-group--dev"
        aria-labelledby="help-group-dev-title"
      >
        <header className="help-group-header">
          <h3 id="help-group-dev-title" className="help-group-title">
            Development and local builds
          </h3>
          <p className="help-group-intro">
            Controls marked <strong>Dev only</strong> are hidden only when the frontend is built with{" "}
            <code>VITE_STRICT_PROD=true</code> (hardened release). Otherwise they appear in both{" "}
            <code>npm run dev</code> and default <code>npm run build</code> output.{" "}
            {strictProd ? (
              <>
                This session was built with strict mode — you will not see those controls; this section
                documents them.
              </>
            ) : (
              <>They match the Dev only controls in this UI.</>
            )}
          </p>
        </header>
        <div className="help-group-body">
          <section className="help-section">
            <h4 className="help-section-title">Focus your pipeline</h4>
            <p>
              This block appears in <strong>all</strong> builds. <strong>Risk tier</strong> presets set{" "}
              <code>min_risk</code> for <code>GET /api/at-risk</code>. A <strong>Fine-tune cutoff</strong>{" "}
              slider (0–100%, 5% steps) appears in non-strict builds only.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">Re-score only (no reload)</h4>
            <p>
              Toolbar control next to <strong>Refresh</strong>, labeled <strong>Dev only</strong>. It is
              visible in default builds; it is hidden or disabled when <code>VITE_STRICT_PROD=true</code>
              . When enabled, it runs the scoring model again on snapshots <em>already in memory</em>{" "}
              without re-reading data files — quick for model tweaks. Use <strong>Refresh</strong> when
              you need to reload JSON / enrichment from disk and then score.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">Demo copy in venue detail</h4>
            <p>
              The churn driver line is labeled <strong>Churn driver (demo narrative)</strong> in dev to
              signal illustrative text; production uses <strong>Primary churn driver:</strong>.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">Raw explanation (JSON)</h4>
            <p>
              In venue detail, a <strong>Raw explanation (JSON)</strong> disclosure expands to the
              structured explainer payload — useful for debugging the LLM/agent output when{" "}
              <code>LLM_API_KEY</code> (or equivalent) is configured on the server.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">Outreach dry run (dev)</h4>
            <p>
              <strong>Dry run (filtered list)</strong> on the toolbar calls{" "}
              <code>POST /api/outreach/bulk-preview</code> with <code>preview_to_email</code>{" "}
              (non-production only): <strong>one</strong> summary email to your dev inbox and{" "}
              <strong>one</strong> Slack message (digest). Both explain which venues, brands, and
              product surfaces are in scope, and how many separate emails and Slack posts would fire in
              production (typically one of each per venue × product surface). The email also includes
              AM-style templates grouped by venue for readability. Requires SMTP and{" "}
              <code>SLACK_BOT_TOKEN</code> on the server. The JSON response is shown on the main page.
            </p>
            <p>
              <strong>Send sample feedback</strong> (venue detail) — smoke test of{" "}
              <code>POST /api/feedback</code>.
            </p>
          </section>
          <section className="help-section">
            <h4 className="help-section-title">Demo data note</h4>
            <p>
              The at-risk table footnote may reference local files (for example enrichment JSON). In
              production, brand and geography come from your warehouse joins.
            </p>
          </section>
        </div>
      </section>
    </div>
  );
}

/** Large static tree — only re-render when strictProd changes. */
export const HelpInstructions = memo(HelpInstructionsInner);
