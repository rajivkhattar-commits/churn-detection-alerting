"""Outreach requests, dry-run, and audit trail."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.contracts.cohort import EnterpriseCohortKey, ProductCode


class OutreachChannel(str, Enum):
    SLACK = "slack"
    EMAIL = "email"


class OutreachStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DRY_RUN = "dry_run"


class OutreachRequest(BaseModel):
    """Trigger outreach to internal owners (or dry-run)."""

    cohort: EnterpriseCohortKey
    product: ProductCode
    channels: List[OutreachChannel] = Field(default_factory=lambda: [OutreachChannel.SLACK])
    template_id: str = "default_internal_alert"
    dry_run: bool = False
    idempotency_key: Optional[str] = None
    slack_channel_or_user: Optional[str] = None
    email_to: Optional[List[str]] = None
    # Non-production only: send the rendered email (and Slack text in the body) here instead of AM routing.
    preview_to_email: Optional[str] = None
    # Filled by the API from venue enrichment for AM-facing templates (client values are overwritten).
    context_brand_name: Optional[str] = None


class OutreachDryRunResult(BaseModel):
    """Rendered payloads without sending."""

    would_send_slack: Optional[str] = None
    would_send_email_subject: Optional[str] = None
    would_send_email_body: Optional[str] = None
    idempotency_key: str


class OutreachBulkPreviewRow(BaseModel):
    """One venue × product surface for a dev batch email."""

    venue_id: str
    product: ProductCode
    market: Optional[str] = None
    country_code: Optional[str] = None


class OutreachBulkPreviewRequest(BaseModel):
    """Dry run: one summary email + one Slack digest; body grouped by venue for the email."""

    preview_to_email: str
    template_id: str = "am_churn_alert"
    rows: List[OutreachBulkPreviewRow] = Field(
        ...,
        min_length=1,
        description="Deduplicated server-side by (venue_id, product); order preserved by first occurrence.",
    )
    slack_channel_or_user: Optional[str] = Field(
        None,
        description="Destination for the single dry-run Slack digest; defaults to #churn-alerts.",
    )


class OutreachBulkPreviewResult(BaseModel):
    """Dry run: one email + one Slack with counts; production would send one email + one Slack per surface."""

    ok: bool = True
    error_message: Optional[str] = None
    preview_to_email: str
    slack_channel_or_user: Optional[str] = None
    venue_count: int
    surface_count: int
    dry_run_email_messages: int = 1
    dry_run_slack_messages: int = 1
    production_email_messages: int = 0
    production_slack_messages: int = 0
    would_send_email_subject: str
    would_send_email_body: str
    would_send_slack: Optional[str] = None
    idempotency_key: str


class OutreachAuditEntry(BaseModel):
    """Append-only audit for compliance and improvement metrics."""

    id: str
    idempotency_key: str
    cohort: EnterpriseCohortKey
    product: ProductCode
    channel: OutreachChannel
    status: OutreachStatus
    template_id: str
    payload_summary: str
    created_at: datetime
    error_message: Optional[str] = None
