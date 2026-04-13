"""Human feedback on explanations for the improvement loop."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.contracts.cohort import EnterpriseCohortKey, ProductCode


class ExplanationFeedback(BaseModel):
    """Feedback tied to a score run and optional hypothesis index."""

    venue_id: str
    product: ProductCode
    run_id: str
    hypothesis_index: Optional[int] = None
    rating: Literal["correct", "partial", "wrong"]
    comment: Optional[str] = None
    submitted_at: datetime
    submitter_id: Optional[str] = None


class FeedbackPayload(BaseModel):
    """API body for submitting feedback."""

    cohort: EnterpriseCohortKey
    product: ProductCode
    run_id: str
    hypothesis_index: Optional[int] = None
    rating: Literal["correct", "partial", "wrong"]
    comment: Optional[str] = None
