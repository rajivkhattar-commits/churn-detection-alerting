"""Score output: risk and churn-type distribution."""

from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.contracts.cohort import EnterpriseCohortKey, ProductCode


class ChurnType(str, Enum):
    """Churn categories for scoring layer."""

    HARD = "hard"
    SOFT = "soft"
    OPERATIONAL = "operational"


class ScoreRow(BaseModel):
    """One scored venue × product for a run."""

    cohort: EnterpriseCohortKey
    product: ProductCode
    as_of_date: date
    scored_at: datetime
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Calibrated P(churn-like outcome)")
    churn_type_probs: Dict[str, float] = Field(
        default_factory=dict,
        description="Soft distribution over hard / soft / operational",
    )
    model_version: str = "baseline_v1"
    run_id: str = ""


class ScoreHistoryPoint(BaseModel):
    """Time series point for UI sparkline."""

    as_of_date: date
    risk_score: float
    churn_type_probs: Dict[str, float] = Field(default_factory=dict)


class AgentEvidence(BaseModel):
    """Single cited signal for an explanation."""

    metric_id: str
    window: str
    value: str
    direction: Optional[str] = Field(None, description="up | down | flat")


class RootCauseHypothesis(BaseModel):
    """Structured agent output per hypothesis."""

    category: str = Field(
        ...,
        description="e.g. renovation, sales_decline, misconfiguration, competitive, unknown",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    summary: str
    evidence: List[AgentEvidence] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)


class AgentExplanation(BaseModel):
    """Full explanation block stored with the score."""

    hypotheses: List[RootCauseHypothesis] = Field(default_factory=list)
    raw_model: Optional[str] = Field(None, description="LLM id for audit")
    prompt_version: str = "v1"
