"""Orchestrate baseline model + explainer + in-memory persistence.

Snowflake is read-only (SELECT) when used for features — no INSERT/DELETE to the warehouse.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.agent.explainer import explain_snapshot
from app.contracts.features import FeatureSnapshot
from app.contracts.scores import AgentExplanation, ScoreRow
from app.ml.baseline import BaselineChurnModel
from app.store.memory import MemoryStore, get_memory_store

_model: Optional[BaselineChurnModel] = None


def get_model() -> BaselineChurnModel:
    global _model
    if _model is None:
        _model = BaselineChurnModel()
    return _model


def score_snapshot(
    snapshot: FeatureSnapshot,
    *,
    store: Optional[MemoryStore] = None,
    run_id: Optional[str] = None,
) -> Tuple[ScoreRow, AgentExplanation]:
    model = get_model()
    risk = model.predict_proba_churn(snapshot.features)
    ctype = model.churn_type_probs(snapshot.features, risk)
    rid = run_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    row = ScoreRow(
        cohort=snapshot.cohort,
        product=snapshot.product,
        as_of_date=snapshot.as_of_date,
        scored_at=now,
        risk_score=risk,
        churn_type_probs=ctype,
        model_version="baseline_v1",
        run_id=rid,
    )
    explanation = explain_snapshot(snapshot, risk, ctype)
    mem = store or get_memory_store()
    mem.add_score(row, explanation)
    return row, explanation


def run_batch_score(
    snapshots: List[FeatureSnapshot],
    *,
    store: Optional[MemoryStore] = None,
) -> List[Tuple[ScoreRow, AgentExplanation]]:
    out: List[Tuple[ScoreRow, AgentExplanation]] = []
    for s in snapshots:
        out.append(score_snapshot(s, store=store))
    return out
