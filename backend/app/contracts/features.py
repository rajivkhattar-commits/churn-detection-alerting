"""Feature snapshot: model input and agent context."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.contracts.cohort import EnterpriseCohortKey, ProductCode


class FeatureVector(BaseModel):
    """Numeric features used by the baseline scorer (names align with training)."""

    orders_7d: float = 0.0
    orders_28d: float = 0.0
    gmv_28d: float = 0.0
    orders_wow_change: float = 0.0
    gmv_mom_change: float = 0.0
    login_days_28d: float = 0.0
    support_tickets_28d: float = 0.0
    config_error_rate_28d: float = 0.0
    menu_sync_failures_28d: float = 0.0
    hours_zero_days_28d: float = 0.0
    peer_gmv_percentile: float = 50.0


class FeatureSnapshot(BaseModel):
    """Point-in-time snapshot for scoring and explanation."""

    cohort: EnterpriseCohortKey
    product: ProductCode
    as_of_date: date
    computed_at: datetime
    features: FeatureVector
    raw_signals: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional ticket excerpts, config flags, dashboard links",
    )
    feature_version: str = "v1"

    def to_agent_context(self) -> str:
        """Compact text for LLM context."""
        f = self.features
        lines = [
            f"venue_id={self.cohort.venue_id} product={self.product.value} as_of={self.as_of_date}",
            f"orders_7d={f.orders_7d} orders_28d={f.orders_28d} gmv_28d={f.gmv_28d}",
            f"orders_wow_change={f.orders_wow_change} gmv_mom_change={f.gmv_mom_change}",
            f"login_days_28d={f.login_days_28d} support_tickets_28d={f.support_tickets_28d}",
            f"config_error_rate_28d={f.config_error_rate_28d} menu_sync_failures_28d={f.menu_sync_failures_28d}",
            f"hours_zero_days_28d={f.hours_zero_days_28d} peer_gmv_percentile={f.peer_gmv_percentile}",
        ]
        if self.raw_signals:
            lines.append(f"extra={self.raw_signals}")
        return "\n".join(lines)


class ChurnLabelRow(BaseModel):
    """Ground-truth churn for evaluation (stored in Snowflake or CSV)."""

    venue_id: str
    product: ProductCode
    churn_type: str  # hard | soft | operational
    churn_date: date
    notes: Optional[str] = None
