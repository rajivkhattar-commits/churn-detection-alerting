"""Resolve who receives real (non–dry-run) outreach: dev inbox vs production AM."""

from __future__ import annotations

from typing import Optional

from app.config import Settings
from app.contracts.outreach import OutreachChannel, OutreachRequest
from app.integrations.am_assignments import resolve_account_manager_email


class OutreachRoutingError(Exception):
    """Maps to HTTP status in the API layer."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def prepare_outreach_request(
    req: OutreachRequest,
    *,
    settings: Settings,
    brand_name: Optional[str],
    country_code: Optional[str],
) -> OutreachRequest:
    """Apply environment rules. Dry-run requests are unchanged."""
    if req.dry_run:
        return req

    env = (settings.environment or "development").strip().lower()

    preview = (req.preview_to_email or "").strip()
    if preview:
        if env == "production":
            raise OutreachRoutingError(
                400,
                "preview_to_email is not allowed when ENVIRONMENT=production.",
            )
        return req.model_copy(
            update={
                "channels": [OutreachChannel.EMAIL],
                "email_to": [preview],
                "slack_channel_or_user": None,
            }
        )

    if env != "production":
        dev = (settings.outreach_dev_email or "").strip()
        if not dev:
            raise OutreachRoutingError(
                400,
                "Non–dry-run sends in non-production require OUTREACH_DEV_EMAIL "
                "(your inbox) and outbound SMTP settings.",
            )
        return req.model_copy(
            update={
                "channels": [OutreachChannel.EMAIL],
                "email_to": [dev],
                "slack_channel_or_user": None,
            }
        )

    am = resolve_account_manager_email(brand_name, country_code)
    if not am:
        raise OutreachRoutingError(
            422,
            f"No account manager email for brand={brand_name!r} country={country_code!r}. "
            "Populate data/am_assignments.json (or your warehouse-backed source) with "
            "by_brand_country entries or default_account_manager_email.",
        )
    return req.model_copy(
        update={
            "channels": [OutreachChannel.EMAIL],
            "email_to": [am],
            "slack_channel_or_user": None,
        }
    )
