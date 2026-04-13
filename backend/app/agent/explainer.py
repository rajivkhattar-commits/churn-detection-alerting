"""Structured explanation: OpenAI when configured, else deterministic rules."""

from __future__ import annotations

import logging
from typing import Dict, List

from app.config import effective_llm_api_key, effective_llm_model, get_settings
from app.contracts.features import FeatureSnapshot
from app.contracts.scores import AgentEvidence, AgentExplanation, RootCauseHypothesis
from app.llm.chat import chat_completion_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an analyst for enterprise restaurant churn. Given numeric signals, output ONLY valid JSON matching this schema:
{
  "hypotheses": [
    {
      "category": "renovation|sales_decline|misconfiguration|competitive|unknown",
      "confidence": 0.0-1.0,
      "summary": "one sentence",
      "evidence": [{"metric_id": "string", "window": "string", "value": "string", "direction": "up|down|flat|null"}],
      "suggested_actions": ["string"]
    }
  ],
  "prompt_version": "v1"
}
Use evidence.metric_id from known fields: orders_wow_change, gmv_mom_change, config_error_rate_28d, menu_sync_failures_28d, hours_zero_days_28d, peer_gmv_percentile, support_tickets_28d, login_days_28d.
Max 3 hypotheses, sorted by confidence."""


def _augmented_agent_context(snapshot: FeatureSnapshot) -> str:
    """Append ENTERPRISE_DEFINITION_JSON prose when set (from AskWoltAI MCP → env sync)."""
    base = snapshot.to_agent_context()
    try:
        from app.definitions import get_definition_provider

        prov = get_definition_provider()
        if prov.enterprise_metadata().get("has_json"):
            text = prov.enterprise_definition_text()
            if text:
                base = (
                    base
                    + "\n\n--- Business definition (ENTERPRISE_DEFINITION_JSON) ---\n"
                    + text[:4000]
                )
    except Exception as e:
        logger.warning("Could not attach enterprise definition to LLM context: %s", e)
    return base


def explain_snapshot(
    snapshot: FeatureSnapshot,
    risk_score: float,
    churn_type_probs: Dict[str, float],
) -> AgentExplanation:
    settings = get_settings()
    if effective_llm_api_key(settings):
        try:
            return _explain_llm(snapshot, risk_score, churn_type_probs, settings)
        except Exception as e:
            logger.warning("LLM explanation failed: %s", e)
    return _explain_heuristic(snapshot, risk_score, churn_type_probs)


def _explain_llm(
    snapshot: FeatureSnapshot,
    risk_score: float,
    churn_type_probs: Dict[str, float],
    settings,
) -> AgentExplanation:
    user = (
        f"risk_score={risk_score:.3f} churn_type_probs={churn_type_probs}\n"
        f"{_augmented_agent_context(snapshot)}"
    )
    data = chat_completion_json(SYSTEM_PROMPT, user, settings=settings)
    hyps: List[RootCauseHypothesis] = []
    for h in data.get("hypotheses", [])[:5]:
        evs = []
        for e in h.get("evidence") or []:
            evs.append(
                AgentEvidence(
                    metric_id=str(e.get("metric_id", "")),
                    window=str(e.get("window", "28d")),
                    value=str(e.get("value", "")),
                    direction=e.get("direction"),
                )
            )
        hyps.append(
            RootCauseHypothesis(
                category=str(h.get("category", "unknown")),
                confidence=float(h.get("confidence", 0.5)),
                summary=str(h.get("summary", "")),
                evidence=evs,
                suggested_actions=list(h.get("suggested_actions") or []),
            )
        )
    return AgentExplanation(
        hypotheses=hyps,
        raw_model=effective_llm_model(settings),
        prompt_version=data.get("prompt_version", "v1"),
    )


def _explain_heuristic(
    snapshot: FeatureSnapshot,
    risk_score: float,
    churn_type_probs: Dict[str, float],
) -> AgentExplanation:
    f = snapshot.features
    hyps: List[RootCauseHypothesis] = []

    if f.hours_zero_days_28d >= 3 or f.orders_28d < 1:
        hyps.append(
            RootCauseHypothesis(
                category="renovation",
                confidence=min(0.85, 0.4 + 0.08 * f.hours_zero_days_28d),
                summary="Operational closure pattern: extended zero-hours or near-zero orders may indicate renovation or temporary closure.",
                evidence=[
                    AgentEvidence(
                        metric_id="hours_zero_days_28d",
                        window="28d",
                        value=str(f.hours_zero_days_28d),
                        direction="up",
                    ),
                    AgentEvidence(
                        metric_id="orders_28d",
                        window="28d",
                        value=str(f.orders_28d),
                        direction="down",
                    ),
                ],
                suggested_actions=[
                    "Verify temporary closure / renovation with the account owner.",
                    "Confirm opening hours and POS hours alignment.",
                ],
            )
        )

    if f.orders_wow_change < -0.1 or f.peer_gmv_percentile < 30:
        hyps.append(
            RootCauseHypothesis(
                category="sales_decline",
                confidence=min(0.9, 0.45 + abs(f.orders_wow_change)),
                summary="Demand or basket weakness versus peers: declining week-over-week orders and/or low peer percentile.",
                evidence=[
                    AgentEvidence(
                        metric_id="orders_wow_change",
                        window="7d_vs_prior",
                        value=f"{f.orders_wow_change:.2f}",
                        direction="down",
                    ),
                    AgentEvidence(
                        metric_id="peer_gmv_percentile",
                        window="28d",
                        value=f"{f.peer_gmv_percentile:.0f}",
                        direction="down",
                    ),
                ],
                suggested_actions=[
                    "Review promos, menu pricing, and local competition.",
                    "Offer growth playbook and marketing support.",
                ],
            )
        )

    if f.config_error_rate_28d > 0.05 or f.menu_sync_failures_28d > 3:
        hyps.append(
            RootCauseHypothesis(
                category="misconfiguration",
                confidence=min(0.88, 0.5 + f.config_error_rate_28d),
                summary="Integration or configuration stress: elevated sync failures or config errors can suppress realized volume.",
                evidence=[
                    AgentEvidence(
                        metric_id="config_error_rate_28d",
                        window="28d",
                        value=f"{f.config_error_rate_28d:.2f}",
                        direction="up",
                    ),
                    AgentEvidence(
                        metric_id="menu_sync_failures_28d",
                        window="28d",
                        value=str(int(f.menu_sync_failures_28d)),
                        direction="up",
                    ),
                ],
                suggested_actions=[
                    "Run integration health check and reconcile menu/POS mappings.",
                    "Escalate to technical support if errors persist.",
                ],
            )
        )

    if churn_type_probs.get("soft", 0) > churn_type_probs.get("hard", 0) and f.support_tickets_28d > 2:
        hyps.append(
            RootCauseHypothesis(
                category="competitive",
                confidence=0.55,
                summary="Soft churn pattern with elevated support contacts may indicate evaluation of alternatives or friction.",
                evidence=[
                    AgentEvidence(
                        metric_id="support_tickets_28d",
                        window="28d",
                        value=str(int(f.support_tickets_28d)),
                        direction="up",
                    )
                ],
                suggested_actions=["Schedule QBR; clarify roadmap and resolve open tickets."],
            )
        )

    if not hyps:
        hyps.append(
            RootCauseHypothesis(
                category="unknown",
                confidence=0.4,
                summary="Insufficient distinctive signals; monitor trend and enrich with CRM / on-site notes.",
                evidence=[],
                suggested_actions=["Add qualitative context in CRM.", "Compare to market cohort next week."],
            )
        )

    hyps.sort(key=lambda h: -h.confidence)
    return AgentExplanation(hypotheses=hyps[:3], raw_model=None, prompt_version="v1-heuristic")
