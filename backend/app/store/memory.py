"""In-memory store for demo and when Snowflake is unavailable."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.contracts.cohort import EnterpriseCohortKey, ProductCode
from app.contracts.features import FeatureSnapshot, FeatureVector
from app.contracts.feedback import ExplanationFeedback
from app.contracts.scores import AgentExplanation, ScoreHistoryPoint, ScoreRow

logger = logging.getLogger(__name__)


def _repo_data_path(name: str) -> Path:
    return Path(__file__).resolve().parents[3] / "data" / name


def _load_demo_snapshots_from_json() -> List[Tuple[EnterpriseCohortKey, ProductCode, FeatureVector, Dict[str, Any]]]:
    """Load MCP-backed demo rows from data/demo_feature_snapshots.json."""
    path = _repo_data_path("demo_feature_snapshots.json")
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Failed to load %s: %s", path, e)
        return []
    out: List[Tuple[EnterpriseCohortKey, ProductCode, FeatureVector, Dict[str, Any]]] = []
    meta_source = data.get("source", "")
    for s in data.get("snapshots", []):
        fv = FeatureVector(**s["features"])
        cohort = EnterpriseCohortKey(
            venue_id=s["venue_id"],
            merchant_id=s.get("merchant_id"),
            market=s.get("market"),
            country_code=s.get("country_code"),
        )
        prod = ProductCode(s["product"])
        raw: Dict[str, Any] = {
            "demo_venue_name": s.get("demo_venue_name"),
            "demo_risk_tier": s.get("demo_risk_tier"),
            "volume_segment": s.get("volume_segment"),
            "orders_90d": s.get("orders_90d"),
            "churn_reason_summary": s.get("churn_reason_summary"),
            "demo_feature_source": meta_source,
        }
        out.append((cohort, prod, fv, raw))
    return out


class MemoryStore:
    def __init__(self) -> None:
        self._snapshots: Dict[Tuple[str, str], FeatureSnapshot] = {}
        self._scores: List[ScoreRow] = []
        self._explanations: Dict[Tuple[str, str, str], AgentExplanation] = {}
        self._feedback: List[ExplanationFeedback] = []

    def seed_demo(self) -> None:
        rows = _load_demo_snapshots_from_json()
        if not rows:
            logger.warning("demo_feature_snapshots.json missing or empty; seeding minimal fallback")
            rows = _fallback_demo_rows()

        today = date.today()
        now = datetime.now(timezone.utc)
        for cohort, prod, fv, raw in rows:
            snap = FeatureSnapshot(
                cohort=cohort,
                product=prod,
                as_of_date=today,
                computed_at=now,
                features=fv,
                raw_signals=raw,
            )
            self._snapshots[(cohort.venue_id, prod.value)] = snap

    def list_snapshots(self) -> List[FeatureSnapshot]:
        return list(self._snapshots.values())

    def get_snapshot(self, venue_id: str, product: ProductCode) -> Optional[FeatureSnapshot]:
        return self._snapshots.get((venue_id, product.value))

    def add_score(
        self,
        row: ScoreRow,
        explanation: Optional[AgentExplanation],
    ) -> None:
        self._scores.append(row)
        self._explanations[(row.cohort.venue_id, row.product.value, row.run_id)] = explanation or AgentExplanation()

    def list_latest_scores(self) -> List[Tuple[ScoreRow, Optional[AgentExplanation]]]:
        """Latest score per venue×product."""
        best: Dict[Tuple[str, str], Tuple[ScoreRow, Optional[AgentExplanation]]] = {}
        for s in self._scores:
            k = (s.cohort.venue_id, s.product.value)
            ex = self._explanations.get((s.cohort.venue_id, s.product.value, s.run_id))
            if k not in best or s.scored_at > best[k][0].scored_at:
                best[k] = (s, ex)
        return list(best.values())

    def history(self, venue_id: str, product: ProductCode) -> List[ScoreHistoryPoint]:
        pts: List[ScoreHistoryPoint] = []
        for s in self._scores:
            if s.cohort.venue_id == venue_id and s.product == product:
                pts.append(
                    ScoreHistoryPoint(
                        as_of_date=s.as_of_date,
                        risk_score=s.risk_score,
                        churn_type_probs=s.churn_type_probs,
                    )
                )
        pts.sort(key=lambda p: p.as_of_date)
        return pts

    def add_feedback(self, fb: ExplanationFeedback) -> None:
        self._feedback.append(fb)


def _fallback_demo_rows() -> List[Tuple[EnterpriseCohortKey, ProductCode, FeatureVector, Dict[str, Any]]]:
    """Minimal rows if JSON is absent (e.g. broken checkout)."""
    return [
        (
            EnterpriseCohortKey(venue_id="demo_fallback_1", market="HEL", country_code="FIN"),
            ProductCode.CLASSIC,
            FeatureVector(orders_28d=40, orders_wow_change=-0.2, peer_gmv_percentile=20),
            {"demo_venue_name": "Fallback demo venue"},
        ),
    ]


_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
        _store.seed_demo()
    return _store


def reload_memory_store() -> MemoryStore:
    """Drop in-memory scores, clear venue enrichment cache, reload snapshots from disk (demo / file-backed)."""
    global _store
    from app.integrations.venue_enrichment import clear_enrichment_cache

    clear_enrichment_cache()
    _store = MemoryStore()
    _store.seed_demo()
    return _store
