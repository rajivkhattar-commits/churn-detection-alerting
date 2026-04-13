"""Shared API and persistence contracts for churn detection."""

from app.contracts.cohort import EnterpriseCohortKey, ProductCode
from app.contracts.features import ChurnLabelRow, FeatureSnapshot, FeatureVector
from app.contracts.scores import (
    AgentEvidence,
    AgentExplanation,
    ChurnType,
    RootCauseHypothesis,
    ScoreHistoryPoint,
    ScoreRow,
)
from app.contracts.outreach import (
    OutreachAuditEntry,
    OutreachChannel,
    OutreachDryRunResult,
    OutreachRequest,
    OutreachStatus,
)
from app.contracts.feedback import ExplanationFeedback, FeedbackPayload

__all__ = [
    "EnterpriseCohortKey",
    "ProductCode",
    "ChurnLabelRow",
    "FeatureSnapshot",
    "FeatureVector",
    "ChurnType",
    "ScoreRow",
    "ScoreHistoryPoint",
    "AgentEvidence",
    "AgentExplanation",
    "RootCauseHypothesis",
    "OutreachAuditEntry",
    "OutreachChannel",
    "OutreachDryRunResult",
    "OutreachRequest",
    "OutreachStatus",
    "ExplanationFeedback",
    "FeedbackPayload",
]
