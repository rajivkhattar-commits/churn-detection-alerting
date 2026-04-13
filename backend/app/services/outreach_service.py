"""Slack and email playbooks with idempotency. Audit is logged locally (no Snowflake DML)."""

from __future__ import annotations

import hashlib
import json
import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Tuple

from app.config import get_settings
from app.contracts.cohort import EnterpriseCohortKey, ProductCode
from app.contracts.outreach import (
    OutreachAuditEntry,
    OutreachBulkPreviewRequest,
    OutreachBulkPreviewResult,
    OutreachBulkPreviewRow,
    OutreachChannel,
    OutreachDryRunResult,
    OutreachRequest,
    OutreachStatus,
)
from app.contracts.scores import ScoreRow
from app.contracts.scores import AgentExplanation
from app.integrations.venue_enrichment import enrichment_for_venue
from app.ui_copy import (
    CHURN_TYPE_HELP,
    SCORE_MEANING,
    product_display_name,
    risk_band,
)

logger = logging.getLogger(__name__)


def _log_outreach_audit(entry: OutreachAuditEntry) -> None:
    logger.info(
        "outreach_audit id=%s channel=%s status=%s venue=%s product=%s",
        entry.id,
        entry.channel.value,
        entry.status.value,
        entry.cohort.venue_id,
        entry.product.value,
    )


def _idempotency_key(req: OutreachRequest, body: str) -> str:
    raw = f"{req.cohort.venue_id}|{req.product.value}|{req.template_id}|{body[:500]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


def _bulk_idempotency_key(req: OutreachBulkPreviewRequest, email_body: str, slack_text: str) -> str:
    raw = f"bulk|{req.preview_to_email}|{req.template_id}|{email_body[:1500]}|{slack_text[:1500]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


def _bulk_inventory_email_lines(
    venue_order: List[str],
    by_venue: Dict[str, List[OutreachBulkPreviewRow]],
) -> List[str]:
    lines: List[str] = []
    for vid in venue_order:
        enr = enrichment_for_venue(vid)
        brand = (enr.get("brand_name") if enr else None) or "—"
        plabels = [product_display_name(br.product.value) for br in by_venue[vid]]
        lines.append(f"  • {vid}  —  {brand}  —  {', '.join(plabels)}")
    return lines


def _bulk_slack_digest(
    *,
    venue_count: int,
    surface_count: int,
    preview_email: str,
    venue_order: List[str],
    by_venue: Dict[str, List[OutreachBulkPreviewRow]],
    slack_dest: str,
) -> str:
    """Single Slack post: summary, production-equivalent counts, venue / brand / product inventory."""
    prod_emails = surface_count
    prod_slack = surface_count
    lines_sl: List[str] = [
        ":clipboard: *Churn outreach — dry run (filtered batch)*",
        "",
        f"*This dry run:* 1 email + 1 Slack message (this post to {slack_dest})",
        f"*Production equivalent:* {prod_emails} outbound email(s) + {prod_slack} Slack message(s)",
        "  _(one email and one Slack post per venue × product surface, matching single-row outreach.)_",
        "",
        f"*Unique venues:* {venue_count}  ·  *Surfaces:* {surface_count}",
        "",
        "*Inventory (venue → brand → product surfaces):*",
    ]
    max_venues = 80
    for i, vid in enumerate(venue_order):
        if i >= max_venues:
            rest = len(venue_order) - max_venues
            lines_sl.append(f"… _and {rest} more venue(s) — see the dry-run email for the full list._")
            break
        enr = enrichment_for_venue(vid)
        brand = (enr.get("brand_name") if enr else None) or "—"
        plabels = [product_display_name(br.product.value) for br in by_venue[vid]]
        lines_sl.append(f"• `{vid}` — *{brand}* — {', '.join(plabels)}")

    lines_sl.extend(
        [
            "",
            f"_Full AM-style template previews are grouped in the dry-run email to {preview_email}._",
        ]
    )
    return "\n".join(lines_sl)


def send_bulk_preview_email(
    req: OutreachBulkPreviewRequest,
    *,
    settings,
    store,
) -> OutreachBulkPreviewResult:
    """Dry run: one summary email + one Slack digest; email body groups per-surface templates by venue."""
    score_map: Dict[Tuple[str, str], Tuple[ScoreRow, Optional[AgentExplanation]]] = {}
    for row, ex in store.list_latest_scores():
        score_map[(row.cohort.venue_id, row.product.value)] = (row, ex)

    seen_pairs: set[Tuple[str, str]] = set()
    venue_order: List[str] = []
    by_venue: Dict[str, List[OutreachBulkPreviewRow]] = {}
    for r in req.rows:
        key = (r.venue_id, r.product.value)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        vid = r.venue_id
        if vid not in by_venue:
            by_venue[vid] = []
            venue_order.append(vid)
        by_venue[vid].append(r)

    surface_count = len(seen_pairs)
    venue_count = len(venue_order)
    prod_emails = surface_count
    prod_slack = surface_count
    slack_dest = (req.slack_channel_or_user or "").strip() or "#churn-alerts"
    preview_addr = (req.preview_to_email or "").strip()

    inventory_lines = _bulk_inventory_email_lines(venue_order, by_venue)
    intro = [
        "=" * 80,
        "DRY RUN — what this sends vs production",
        "=" * 80,
        "",
        f"This dry run delivers:  1 email (this message)  +  1 Slack message (summary digest to {slack_dest})",
        "",
        f"In production for this cohort:  {prod_emails} outbound email(s)  +  {prod_slack} Slack message(s)",
        "  (One email and one Slack post per venue × product surface, matching single-row outreach.)",
        "",
        f"Unique venues: {venue_count}",
        f"Venue × product surfaces in scope: {surface_count}",
        "",
        "Inventory (venue → brand → product surfaces):",
        *inventory_lines,
        "",
        "Below: AM-style templates grouped by venue (for readability). Production sends one email per surface, not one bulk email.",
        "=" * 80,
        "",
    ]
    parts: List[str] = list(intro)

    for vi, vid in enumerate(venue_order, 1):
        enr = enrichment_for_venue(vid)
        brand_disp = enr.get("brand_name") if enr else None
        brand_header = brand_disp or "—"
        cc_default = (enr.get("country_code") if enr else None) or None
        subs = by_venue[vid]
        parts.append("\n" + "=" * 80)
        parts.append(f"VENUE {vi}/{venue_count}  |  {vid}")
        parts.append(f"Brand: {brand_header}  |  {len(subs)} product surface(s)")
        parts.append("=" * 80)

        for pj, br in enumerate(subs, 1):
            product = br.product
            cohort = EnterpriseCohortKey(
                venue_id=vid,
                merchant_id=None,
                market=br.market,
                country_code=br.country_code or cc_default,
            )
            lookup = score_map.get((vid, product.value))
            if lookup:
                score_row, explanation = lookup
                risk = score_row.risk_score
                churn_type_probs = dict(score_row.churn_type_probs or {})
            else:
                risk = 0.0
                explanation = None
                churn_type_probs = {}

            slack_text, email_subj, email_body = render_message(
                req.template_id,
                cohort,
                product,
                risk,
                explanation,
                churn_type_probs=churn_type_probs or None,
                brand_display=brand_disp,
            )
            combined = (
                f"{email_body}\n\n"
                "--- Per-surface Slack template (in production each surface is its own Slack message; shown here for reference) ---\n\n"
                f"{slack_text}"
            )
            plabel = product_display_name(product.value)
            parts.append(
                f"\n--- Product surface {pj}/{len(subs)}: {plabel} — per-surface email subject would be: {email_subj} ---\n"
            )
            parts.append(combined)
            parts.append("")

    full_body = "\n".join(parts).strip() + "\n"
    subject = (
        f"[Churn dry run] {venue_count} venues · {surface_count} surfaces — 1 email + 1 Slack"
    )
    slack_text = _bulk_slack_digest(
        venue_count=venue_count,
        surface_count=surface_count,
        preview_email=preview_addr,
        venue_order=venue_order,
        by_venue=by_venue,
        slack_dest=slack_dest,
    )
    id_key = _bulk_idempotency_key(req, full_body, slack_text)

    email_err = _send_email(subject, full_body, [preview_addr], settings)
    if email_err:
        logger.warning("bulk dry-run email failed: %s", email_err)

    slack_err = _send_slack(slack_text, req.slack_channel_or_user, settings)
    if slack_err:
        logger.warning("bulk dry-run slack failed: %s", slack_err)

    errs: List[str] = []
    if email_err:
        errs.append(f"email: {email_err}")
    if slack_err:
        errs.append(f"slack: {slack_err}")
    combined_err = "; ".join(errs) if errs else None

    return OutreachBulkPreviewResult(
        ok=not errs,
        error_message=combined_err,
        preview_to_email=preview_addr,
        slack_channel_or_user=slack_dest,
        venue_count=venue_count,
        surface_count=surface_count,
        dry_run_email_messages=1,
        dry_run_slack_messages=1,
        production_email_messages=prod_emails,
        production_slack_messages=prod_slack,
        would_send_email_subject=subject,
        would_send_email_body=full_body,
        would_send_slack=slack_text,
        idempotency_key=id_key,
    )


def _format_churn_mix(probs: Optional[Dict[str, float]]) -> str:
    if not probs:
        return "— (not available)"
    parts = []
    for k in ("hard", "soft", "operational"):
        v = probs.get(k)
        if v is not None:
            parts.append(f"{k.capitalize()}: {v:.0%}")
    return " | ".join(parts) if parts else "—"


def render_message(
    template_id: str,
    cohort: EnterpriseCohortKey,
    product: ProductCode,
    risk: float,
    explanation: Optional[AgentExplanation],
    churn_type_probs: Optional[Dict[str, float]] = None,
    *,
    brand_display: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Return (slack markdown text, email subject, plain-text email body)."""
    band_label, band_detail = risk_band(risk)
    product_label = product_display_name(product.value)
    top_summary = "No hypothesis generated yet."
    top_action = "Review account in internal dashboards and Snowflake ENT views."
    if explanation and explanation.hypotheses:
        h0 = explanation.hypotheses[0]
        top_summary = h0.summary
        top_action = h0.suggested_actions[0] if h0.suggested_actions else top_action

    loc = " / ".join(
        x
        for x in (
            cohort.market,
            cohort.country_code,
        )
        if x
    ) or "location n/a"

    if template_id == "am_churn_alert":
        brand_line = brand_display or "—"
        slack_lines = [
            f":email: *Churn alert (account manager)* — `{template_id}`",
            f"*Brand:* {brand_line}",
            f"*Venue* `{cohort.venue_id}` · {loc}",
            f"*Product surface:* {product_label}",
            f"*Risk:* *{risk:.0%}* — _{band_label}_",
            f"_{band_detail}_",
            "",
            f"*Churn-style mix (heuristic):* {_format_churn_mix(churn_type_probs)}",
            "",
            f"*Top hypothesis:* {top_summary}",
            f"*Suggested next step:* {top_action}",
            "",
            f"_What risk % means:_ {SCORE_MEANING[:200]}…",
        ]
        slack = "\n".join(slack_lines)
        email_subj = (
            f"[Churn risk] {brand_line} — {product_label} — {cohort.country_code or loc} ({risk:.0%})"
        )
        mix = _format_churn_mix(churn_type_probs)
        email_body = f"""Churn-risk alert — account manager

Brand: {brand_line}
Venue ID: {cohort.venue_id}
Location: {loc}
Product surface: {product_label}

Risk score: {risk:.0%} — {band_label}
{band_detail}

What this score means:
{SCORE_MEANING}

Churn-style mix (heuristic — not mutually exclusive in production):
{mix}
{CHURN_TYPE_HELP}

Top hypothesis:
{top_summary}

Suggested next step:
{top_action}

---
Template: {template_id}
"""
        return slack, email_subj, email_body

    slack_lines = [
        f":rotating_light: *Enterprise churn alert* — `{template_id}`",
        f"*Venue* `{cohort.venue_id}` · {loc}",
        f"*Product surface:* {product_label}",
        f"*Risk:* *{risk:.0%}* — _{band_label}_",
        f"_{band_detail}_",
        "",
        f"*Churn-style mix (heuristic):* {_format_churn_mix(churn_type_probs)}",
        "",
        f"*Top hypothesis:* {top_summary}",
        f"*Suggested next step:* {top_action}",
        "",
        f"_What risk % means:_ {SCORE_MEANING[:200]}…",
    ]
    slack = "\n".join(slack_lines)

    email_subj = f"[ENT churn] {band_label} — {product_label} — {cohort.venue_id[:12]}… ({risk:.0%})"

    mix = _format_churn_mix(churn_type_probs)
    email_body = f"""Enterprise churn alert — internal

Venue ID: {cohort.venue_id}
Location: {loc}
Product surface: {product_label}

Risk score: {risk:.0%} — {band_label}
{band_detail}

What this score means:
{SCORE_MEANING}

Churn-style mix (heuristic — not mutually exclusive in production):
{mix}
{CHURN_TYPE_HELP}

Top hypothesis:
{top_summary}

Suggested next step:
{top_action}

---
Template: {template_id}
"""

    return slack, email_subj, email_body


def send_outreach(
    req: OutreachRequest,
    *,
    risk: float,
    explanation: Optional[AgentExplanation],
    churn_type_probs: Optional[Dict[str, float]] = None,
) -> OutreachDryRunResult:
    slack_text, email_subj, email_body = render_message(
        req.template_id,
        req.cohort,
        req.product,
        risk,
        explanation,
        churn_type_probs=churn_type_probs,
        brand_display=req.context_brand_name,
    )
    preview = (req.preview_to_email or "").strip()
    if preview and not req.dry_run:
        email_body = (
            f"{email_body}\n\n"
            "--- Slack message preview (not sent to Slack in this mode) ---\n\n"
            f"{slack_text}"
        )
    key = req.idempotency_key or _idempotency_key(req, slack_text)

    if req.dry_run:
        entry = OutreachAuditEntry(
            id=str(uuid.uuid4()),
            idempotency_key=key,
            cohort=req.cohort,
            product=req.product,
            channel=OutreachChannel.SLACK,
            status=OutreachStatus.DRY_RUN,
            template_id=req.template_id,
            payload_summary=json.dumps({"slack": slack_text[:2000]}),
            created_at=datetime.now(timezone.utc),
        )
        _log_outreach_audit(entry)
        return OutreachDryRunResult(
            would_send_slack=slack_text,
            would_send_email_subject=email_subj,
            would_send_email_body=email_body,
            idempotency_key=key,
        )

    settings = get_settings()

    for ch in req.channels:
        eid = str(uuid.uuid4())
        if ch == OutreachChannel.SLACK:
            err = _send_slack(slack_text, req.slack_channel_or_user, settings)
            status = OutreachStatus.SENT if not err else OutreachStatus.FAILED
            entry = OutreachAuditEntry(
                id=eid,
                idempotency_key=key + ":slack",
                cohort=req.cohort,
                product=req.product,
                channel=OutreachChannel.SLACK,
                status=status,
                template_id=req.template_id,
                payload_summary=slack_text[:8192],
                created_at=datetime.now(timezone.utc),
                error_message=err,
            )
            _log_outreach_audit(entry)
        elif ch == OutreachChannel.EMAIL:
            err = _send_email(email_subj, email_body, req.email_to, settings)
            status = OutreachStatus.SENT if not err else OutreachStatus.FAILED
            entry = OutreachAuditEntry(
                id=eid,
                idempotency_key=key + ":email",
                cohort=req.cohort,
                product=req.product,
                channel=OutreachChannel.EMAIL,
                status=status,
                template_id=req.template_id,
                payload_summary=email_body[:8192],
                created_at=datetime.now(timezone.utc),
                error_message=err,
            )
            _log_outreach_audit(entry)

    return OutreachDryRunResult(
        would_send_slack=slack_text if OutreachChannel.SLACK in req.channels else None,
        would_send_email_subject=email_subj if OutreachChannel.EMAIL in req.channels else None,
        would_send_email_body=email_body if OutreachChannel.EMAIL in req.channels else None,
        idempotency_key=key,
    )


def _send_slack(text: str, channel_or_user: Optional[str], settings) -> Optional[str]:
    if not settings.slack_bot_token:
        logger.warning("Slack bot token not set; skipping send")
        return "slack_bot_token not configured"
    try:
        from slack_sdk import WebClient

        client = WebClient(token=settings.slack_bot_token)
        dest = channel_or_user or "#churn-alerts"
        client.chat_postMessage(channel=dest, text=text)
        return None
    except Exception as e:
        logger.exception("Slack send failed")
        return str(e)


def _send_email(subject: str, body: str, to_list: Optional[list], settings) -> Optional[str]:
    if not all([settings.smtp_host, settings.smtp_from, to_list]):
        logger.warning("SMTP not fully configured; skipping email")
        return "smtp not configured"
    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = ", ".join(to_list)
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
            s.starttls()
            if settings.smtp_user and settings.smtp_password:
                s.login(settings.smtp_user, settings.smtp_password)
            s.sendmail(settings.smtp_from, to_list, msg.as_string())
        return None
    except Exception as e:
        logger.exception("Email send failed")
        return str(e)
