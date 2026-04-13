"""Cohort keys: Enterprise venue × Wolt product surface."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProductCode(str, Enum):
    """Churn is scored per venue × Wolt product surface (AskWoltAI / PRODUCTION semantics)."""

    CLASSIC = "classic"
    WOLT_PLUS = "wolt_plus"
    TAKEAWAY_PICKUP = "takeaway_pickup"
    DRIVE = "drive"
    WOLT_FOR_WORK = "wolt_for_work"
    PREORDER = "preorder"
    OTHER = "other"

    # Legacy aliases (same string values as before — keep CSV/API compat where used)
    DELIVERY = "classic"
    PICKUP = "takeaway_pickup"
    POS = "other"
    TABLE_ORDER = "other"


class EnterpriseCohortKey(BaseModel):
    """Stable identifiers for Enterprise restaurant scope in Snowflake."""

    venue_id: str = Field(..., description="Internal venue identifier")
    merchant_id: Optional[str] = Field(None, description="Parent merchant / account")
    market: Optional[str] = Field(None, description="City or region code")
    country_code: Optional[str] = Field(
        None,
        min_length=2,
        max_length=3,
        description="ISO 3166-1 alpha-2 or alpha-3 (Snowflake / Enterprise often use alpha-3).",
    )

    model_config = {"frozen": True}
