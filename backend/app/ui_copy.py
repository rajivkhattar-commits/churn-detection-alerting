"""Human-readable labels for UI and outreach (scoring bands, product names)."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

# Aligned with ProductCode string values
PRODUCT_DISPLAY: Dict[str, str] = {
    "classic": "Classic (marketplace delivery)",
    "wolt_plus": "Wolt+",
    "takeaway_pickup": "Takeaway / pickup",
    "drive": "Wolt Drive",
    "wolt_for_work": "Wolt for Work",
    "preorder": "Pre-order",
    "other": "Other",
}


def product_display_name(product_code: str) -> str:
    return PRODUCT_DISPLAY.get(product_code, product_code.replace("_", " ").title())


def risk_band(score: float) -> Tuple[str, str]:
    """Return (short label, one-line explanation) for a 0–1 risk score."""
    s = max(0.0, min(1.0, score))
    if s < 0.35:
        return ("Lower concern", "Typical range for stable ENT accounts; still review drivers if trending up.")
    if s < 0.55:
        return ("Elevated", "Worth a proactive check-in — compare to peer GMV and recent config or hours changes.")
    if s < 0.75:
        return ("High priority", "Strong churn-like signals; align sales/support and confirm operational root causes.")
    return ("Critical", "Severe decline or breakage signals; treat as urgent account review.")


def volume_segment_label(segment: Optional[str]) -> str:
    """Human-readable volume cohort for UI."""
    if segment == "low_volume_ent":
        return "Low (bottom quartile)"
    if segment == "high_volume_ent":
        return "High (top cohort)"
    return ""


def risk_band_key(score: float) -> str:
    """Stable key for UI styling (badges / flags)."""
    s = max(0.0, min(1.0, score))
    if s < 0.35:
        return "lower_concern"
    if s < 0.55:
        return "elevated"
    if s < 0.75:
        return "high_priority"
    return "critical"


def exploration_tips(
    band_key: str,
    product_code: str,
    volume_segment: str | None = None,
) -> str:
    """Short Sales-facing next steps; pair with Snowflake / MCP discovery."""
    product = product_display_name(product_code)
    base: Dict[str, str] = {
        "lower_concern": "Monitor weekly: pull 8–12 week order & GMV trend in Snowflake; confirm hours and menu sync are clean.",
        "elevated": f"Compare peer GMV band for {product}; schedule a light AM touchpoint and review any open support themes.",
        "high_priority": f"Align with support on tickets and config flags; validate Wolt+ / Drive / takeaway settings for {product}.",
        "critical": "Urgent: same-day outreach, ENT lead in the loop; distinguish operational pause vs contractual churn in CRM.",
    }
    tip = base.get(band_key, base["elevated"])
    if volume_segment == "low_volume_ent":
        tip = (
            "Bottom-quartile ENT volume: confirm onboarding/ramp vs structural non-viability; "
            "compare to same-brand peers in Snowflake. " + tip
        )
    return tip + " Use AskWoltAI MCP or dim joins from venue_id to dig into merchant tier and history."


SCORE_MEANING = (
    "Risk score estimates how likely this venue × product looks like a churn-like outcome "
    "in the forward window, using recent orders, GMV trends, configuration health, and support load. "
    "It is not a contractual churn flag — combine with your ENT playbooks and Snowflake truth."
)

CHURN_TYPE_HELP = (
    "Soft / hard / operational split is a heuristic view of churn *style*: "
    "soft = reversible volume decay; hard = durable exit; operational = closures, config, or program pauses."
)
