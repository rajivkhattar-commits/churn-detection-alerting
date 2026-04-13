"""FastAPI application: at-risk list, scoring, outreach, feedback, backtest."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.contracts.cohort import ProductCode
from app.contracts.features import FeatureSnapshot
from app.contracts.feedback import ExplanationFeedback, FeedbackPayload
from app.contracts.outreach import OutreachBulkPreviewRequest, OutreachRequest
from app.contracts.scores import AgentExplanation
from app.definitions import get_definition_provider, mcp_guidance
from app.definitions.provider import canonical_joins_from_env
from app.integrations.am_assignments import clear_am_assignments_cache
from app.integrations.venue_enrichment import enrichment_for_venue
from app.ui_copy import (
    CHURN_TYPE_HELP,
    PRODUCT_DISPLAY,
    SCORE_MEANING,
    exploration_tips,
    product_display_name,
    risk_band,
    risk_band_key,
    volume_segment_label,
)
from app.integrations.askwolt_sync import (
    check_askwolt_clone_updates,
    log_update_status_if_dev,
    pull_askwolt_clone,
)
from app.ml.backtest import run_backtest
from app.services.outreach_service import send_bulk_preview_email, send_outreach
from app.services.outreach_routing import OutreachRoutingError, prepare_outreach_request
from app.services.scoring_service import get_model, run_batch_score
from app.snowflake_db.client import get_snowflake_client
from app.store.memory import get_memory_store, reload_memory_store

app = FastAPI(title="Enterprise Churn Detection", version="0.1.0")


def _orders_90d_from_snapshot(snap: Optional[FeatureSnapshot]) -> Optional[int]:
    """Last-90d order count from snapshot raw_signals, or scaled from orders_28d if missing."""
    if snap is None:
        return None
    rs = snap.raw_signals or {}
    raw = rs.get("orders_90d")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    if snap.features is not None and snap.features.orders_28d:
        return int(round(float(snap.features.orders_28d) * 90.0 / 28.0))
    return None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AtRiskItem(BaseModel):
    brand_name: Optional[str] = None
    city: Optional[str] = None
    country_code: Optional[str] = None
    venue_id: str
    merchant_id: Optional[str]
    market: Optional[str]
    venue_display_name: Optional[str] = None
    volume_segment: Optional[str] = None
    volume_segment_label: str = ""
    orders_90d: Optional[int] = Field(
        None,
        description="Order count in the last 90 days (venue-level; same basis as pipeline exports).",
    )
    product: str
    product_display: str = ""
    churn_likelihood: float = Field(..., description="0–1 calibrated churn-like outcome (same as risk_score).")
    risk_score: float = Field(..., description="Deprecated alias for churn_likelihood; kept for compatibility.")
    risk_band_label: str = ""
    risk_band_key: str = ""
    churn_reason_summary: str = ""
    ai_hypothesis: Optional[str] = None
    exploration_tips: str = ""
    churn_type_probs: dict
    run_id: str


class VenueDetailResponse(BaseModel):
    brand_name: Optional[str] = None
    city: Optional[str] = None
    venue_id: str
    product: str
    venue_display_name: Optional[str] = None
    market: Optional[str] = None
    country_code: Optional[str] = None
    volume_segment: Optional[str] = None
    volume_segment_label: str = ""
    orders_90d: Optional[int] = Field(
        None,
        description="Order count in the last 90 days (venue-level; same basis as pipeline exports).",
    )
    churn_reason_summary: str = ""
    product_display: str = ""
    risk_band_label: str = ""
    risk_band_key: str = ""
    risk_band_detail: str = ""
    exploration_tips: str = ""
    score_meaning: str = ""
    churn_type_help: str = ""
    latest: dict
    explanation: Optional[dict]
    history: List[dict]


class ScoreRunRequest(BaseModel):
    venue_ids: Optional[List[str]] = Field(None, description="If empty, score all demo snapshots")


@app.on_event("startup")
def startup() -> None:
    log_update_status_if_dev()
    get_model()
    store = get_memory_store()
    if not store.list_latest_scores():
        run_batch_score(store.list_snapshots(), store=store)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/ui/copy")
def ui_copy_static() -> dict:
    """Static product labels and scoring copy for the UI."""
    return {
        "product_labels": PRODUCT_DISPLAY,
        "score_meaning": SCORE_MEANING,
        "churn_type_help": CHURN_TYPE_HELP,
    }


@app.get("/api/definitions/enterprise")
def enterprise_definitions() -> dict:
    """Enterprise definition, canonical joins, and MCP tool hints (env populated from Cursor MCP)."""
    p = get_definition_provider()
    return {
        "text": p.enterprise_definition_text(),
        "metadata": p.enterprise_metadata(),
        "canonical_joins": canonical_joins_from_env(),
        "mcp": mcp_guidance(),
    }


@app.get("/api/diagnostics/snowflake")
def snowflake_diagnostics() -> dict:
    """Connection status. Snowflake is read-only from this service — no DML."""
    sf = get_snowflake_client()
    s = get_settings()
    return {
        "credentials_configured": bool(
            s.snowflake_account and s.snowflake_user and s.snowflake_password
        ),
        "connected": sf.available,
        "connect_error": sf.connect_error,
        "database": s.snowflake_database,
        "schema": s.snowflake_schema,
        "snowflake_dml_policy": "disabled",
        "note": "This app sends no INSERT, UPDATE, DELETE, or DDL to Snowflake.",
    }


@app.get("/api/at-risk", response_model=List[AtRiskItem])
def at_risk(
    min_risk: float = Query(
        0.0,
        ge=0.0,
        le=1.0,
        description="Sales filter: only return venues whose risk score is >= this value (0–1, e.g. 0.35 = 35%).",
    ),
) -> List[AtRiskItem]:
    store = get_memory_store()
    items: List[AtRiskItem] = []
    for row, ex in store.list_latest_scores():
        if row.risk_score < min_risk:
            continue
        top = None
        if ex and ex.hypotheses:
            top = ex.hypotheses[0].summary
        snap = store.get_snapshot(row.cohort.venue_id, row.product)
        vname = None
        vol: Optional[str] = None
        churn_sum = ""
        if snap and snap.raw_signals:
            rs = snap.raw_signals
            vname = rs.get("demo_venue_name")
            vol = rs.get("volume_segment")
            churn_sum = str(rs.get("churn_reason_summary") or "")
        band_label, _ = risk_band(row.risk_score)
        bk = risk_band_key(row.risk_score)
        enr = enrichment_for_venue(row.cohort.venue_id)
        city = enr.get("city") or row.cohort.market
        cc = enr.get("country_code") or row.cohort.country_code
        brand = enr.get("brand_name")
        tips = exploration_tips(bk, row.product.value, vol)
        o90 = _orders_90d_from_snapshot(snap)
        items.append(
            AtRiskItem(
                brand_name=brand,
                city=city,
                country_code=cc,
                venue_id=row.cohort.venue_id,
                merchant_id=row.cohort.merchant_id,
                market=row.cohort.market,
                venue_display_name=vname,
                volume_segment=vol,
                volume_segment_label=volume_segment_label(vol),
                orders_90d=o90,
                product=row.product.value,
                product_display=product_display_name(row.product.value),
                churn_likelihood=row.risk_score,
                risk_score=row.risk_score,
                risk_band_label=band_label,
                risk_band_key=bk,
                churn_reason_summary=churn_sum,
                ai_hypothesis=top,
                exploration_tips=tips,
                churn_type_probs=row.churn_type_probs,
                run_id=row.run_id,
            )
        )
    items.sort(key=lambda x: -x.churn_likelihood)
    return items


@app.get("/api/venues/{venue_id}", response_model=VenueDetailResponse)
def venue_detail(venue_id: str, product: ProductCode = Query(...)) -> VenueDetailResponse:
    store = get_memory_store()
    latest = None
    explanation = None
    found = None
    for row, ex in store.list_latest_scores():
        if row.cohort.venue_id == venue_id and row.product == product:
            found = row
            latest = {
                "risk_score": row.risk_score,
                "churn_type_probs": row.churn_type_probs,
                "run_id": row.run_id,
                "as_of_date": str(row.as_of_date),
                "scored_at": row.scored_at.isoformat(),
            }
            explanation = ex.model_dump() if ex else None
            break
    if not latest or found is None:
        raise HTTPException(404, "No score for this venue/product; run /api/score/run first")
    snap = store.get_snapshot(venue_id, product)
    rs = (snap.raw_signals or {}) if snap else {}
    vname = rs.get("demo_venue_name")
    vol = rs.get("volume_segment")
    churn_sum = str(rs.get("churn_reason_summary") or "")
    band_label, band_detail = risk_band(found.risk_score)
    bk = risk_band_key(found.risk_score)
    enr = enrichment_for_venue(venue_id)
    city = enr.get("city") or found.cohort.market
    cc = enr.get("country_code") or found.cohort.country_code
    brand = enr.get("brand_name")
    tips = exploration_tips(bk, product.value, vol)
    hist = [h.model_dump() for h in store.history(venue_id, product)]
    o90 = _orders_90d_from_snapshot(snap)
    return VenueDetailResponse(
        brand_name=brand,
        city=city,
        venue_id=venue_id,
        product=product.value,
        venue_display_name=vname,
        market=found.cohort.market,
        country_code=cc,
        volume_segment=vol,
        volume_segment_label=volume_segment_label(vol),
        orders_90d=o90,
        churn_reason_summary=churn_sum,
        product_display=product_display_name(product.value),
        risk_band_label=band_label,
        risk_band_key=bk,
        risk_band_detail=band_detail,
        exploration_tips=tips,
        score_meaning=SCORE_MEANING,
        churn_type_help=CHURN_TYPE_HELP,
        latest=latest,
        explanation=explanation,
        history=hist,
    )


@app.post("/api/refresh")
def refresh_data() -> dict:
    """Reload feature snapshots + venue enrichment from server files, then re-score all rows.

    Matches the UI **Refresh** action: pick up new demo JSON / exports without restarting the app.
    In production, daily batch jobs typically refresh upstream data; operators use this to pull the
    latest materialized files and scores into the running service.
    """
    clear_am_assignments_cache()
    store = reload_memory_store()
    results = run_batch_score(store.list_snapshots(), store=store)
    run_ids = list({r.run_id for r, _ in results})
    return {
        "ok": True,
        "snapshots": len(store.list_snapshots()),
        "scored": len(results),
        "run_ids": run_ids,
    }


@app.post("/api/score/run")
def score_run(body: ScoreRunRequest) -> Any:
    store = get_memory_store()
    snaps = store.list_snapshots()
    if body.venue_ids:
        snaps = [s for s in snaps if s.cohort.venue_id in set(body.venue_ids)]
    results = run_batch_score(snaps, store=store)
    return {
        "scored": len(results),
        "run_ids": list({r.run_id for r, _ in results}),
        "items": [
            {
                "venue_id": r.cohort.venue_id,
                "product": r.product.value,
                "risk_score": r.risk_score,
                "run_id": r.run_id,
            }
            for r, _ in results
        ],
    }


@app.post("/api/outreach")
def outreach(req: OutreachRequest) -> Any:
    store = get_memory_store()
    risk = 0.0
    churn_type_probs: dict = {}
    explanation: Optional[AgentExplanation] = None
    for row, ex in store.list_latest_scores():
        if row.cohort.venue_id == req.cohort.venue_id and row.product == req.product:
            risk = row.risk_score
            churn_type_probs = dict(row.churn_type_probs or {})
            explanation = ex
            break
    enr = enrichment_for_venue(req.cohort.venue_id)
    brand = enr.get("brand_name") if enr else None
    cc: Optional[str] = (enr.get("country_code") if enr else None) or req.cohort.country_code
    req_routed = req.model_copy(update={"context_brand_name": brand})
    settings = get_settings()
    try:
        req_routed = prepare_outreach_request(
            req_routed,
            settings=settings,
            brand_name=brand,
            country_code=cc,
        )
    except OutreachRoutingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return send_outreach(
        req_routed,
        risk=risk,
        explanation=explanation,
        churn_type_probs=churn_type_probs or None,
    ).model_dump()


@app.post("/api/outreach/bulk-preview")
def outreach_bulk_preview(body: OutreachBulkPreviewRequest) -> Any:
    """Dev-only dry run: 1 summary email + 1 Slack digest; email body groups AM templates by venue."""
    settings = get_settings()
    env = (settings.environment or "development").strip().lower()
    preview = (body.preview_to_email or "").strip()
    if not preview:
        raise HTTPException(status_code=400, detail="preview_to_email is required")
    if env == "production":
        raise HTTPException(
            status_code=400,
            detail="Bulk preview is not allowed when ENVIRONMENT=production.",
        )
    store = get_memory_store()
    return send_bulk_preview_email(body, settings=settings, store=store).model_dump()


@app.post("/api/feedback")
def feedback(body: FeedbackPayload, submitter_id: Optional[str] = None) -> dict:
    fid = str(uuid.uuid4())
    fb = ExplanationFeedback(
        venue_id=body.cohort.venue_id,
        product=body.product,
        run_id=body.run_id,
        hypothesis_index=body.hypothesis_index,
        rating=body.rating,
        comment=body.comment,
        submitted_at=datetime.now(timezone.utc),
        submitter_id=submitter_id,
    )
    get_memory_store().add_feedback(fb)
    return {"id": fid, "status": "ok", "persisted": "memory"}


@app.get("/api/backtest")
def backtest() -> dict:
    return run_backtest(get_model())


@app.get("/api/dev/askwolt-mcp")
def dev_askwolt_status() -> dict:
    """Development only: git status of ask-wolt-mcp clone (behind origin/main)."""
    if not get_settings().debug:
        raise HTTPException(status_code=404, detail="Not found")
    return check_askwolt_clone_updates()


@app.post("/api/dev/askwolt-mcp/sync")
def dev_askwolt_sync() -> dict:
    """Development only: git pull + pip install in the clone; clears schema cache."""
    if not get_settings().debug:
        raise HTTPException(status_code=404, detail="Not found")
    ok, msg = pull_askwolt_clone()
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return {"ok": True, "message": msg}


_static = Path(__file__).resolve().parent.parent / "static"
if _static.is_dir():
    app.mount("/", StaticFiles(directory=str(_static), html=True), name="static")
