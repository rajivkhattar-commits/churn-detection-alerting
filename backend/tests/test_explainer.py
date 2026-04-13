"""Explanation agent: heuristic fallback when LLM unavailable."""

from datetime import date, datetime, timezone

import pytest

from app.agent.explainer import explain_snapshot
from app.contracts.cohort import EnterpriseCohortKey, ProductCode
from app.contracts.features import FeatureSnapshot, FeatureVector


def test_heuristic_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    snap = FeatureSnapshot(
        cohort=EnterpriseCohortKey(venue_id="v1"),
        product=ProductCode.CLASSIC,
        as_of_date=date(2026, 1, 1),
        computed_at=datetime.now(timezone.utc),
        features=FeatureVector(
            orders_wow_change=-0.3,
            hours_zero_days_28d=5,
            menu_sync_failures_28d=10,
            config_error_rate_28d=0.2,
            peer_gmv_percentile=15,
        ),
    )
    ex = explain_snapshot(snap, 0.7, {"hard": 0.2, "soft": 0.5, "operational": 0.3})
    assert ex.hypotheses
    assert ex.raw_model is None
    cats = {h.category for h in ex.hypotheses}
    assert "sales_decline" in cats or "misconfiguration" in cats or "renovation" in cats
