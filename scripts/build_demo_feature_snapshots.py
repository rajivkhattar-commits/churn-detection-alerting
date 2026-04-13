#!/usr/bin/env python3
"""Build data/demo_feature_snapshots.json from data/demo_venues.csv + stratified tiers.

Input **data/demo_venues.csv** — single list of demo ENT venues (high + low volume cohorts),
with `volume_segment` (`high_volume_ent` | `low_volume_ent`). See data/mcp_exploration_notes.txt
for how this file is sourced and how to refresh Snowflake brands.

After one snapshot per CSV row, the script appends **extra product surfaces** for a subset of venues
so the UI can exercise multi-surface / venue-grouped flows (same `venue_id`, different `product`).

Run: python3 scripts/build_demo_feature_snapshots.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEMO_VENUES_CSV = REPO / "data" / "demo_venues.csv"
OUT_PATH = REPO / "data" / "demo_feature_snapshots.json"

PRODUCTS = (
    "classic",
    "wolt_plus",
    "takeaway_pickup",
    "drive",
    "wolt_for_work",
)

def country_alpha3(raw: str) -> str:
    """ISO 3166-1 alpha-3 — matches Snowflake / MCP venue exports."""
    return raw.strip().upper()

# One-liners for UI “churn driver” diversity (paired with volume_segment)
HIGH_CHURN_REASONS = (
    "Peer-relative softness: GMV vs ENT peer set trending down despite healthy throughput.",
    "Operational stress: config/menu/hours signals stacking on a high-volume line.",
    "Mixed: volume still large but engagement and support load point to decay risk.",
    "Margin/commission tension pattern — validate Wolt+ / takeaway mix with finance.",
    "Sharp short-term drop vs prior quarter — investigate local competition or staffing.",
)

LOW_CHURN_REASONS = (
    "Structural low throughput: bottom-quartile ENT orders — viability vs onboarding/ramp.",
    "Persistently minimal orders; likely below sustainable floor for the product line.",
    "Ultra-low activity — distinguish new go-live lag from chronic underperformance.",
    "Low volume + declining week-over-week — compounding churn risk.",
    "Sparse orders and weak peer percentile — prioritize rescue playbook or exit discussion.",
)


def orders_from_90d_high(o90: int) -> tuple[float, float, float]:
    o28 = max(80.0, float(int(o90 * 28 / 90)))
    o7 = max(20.0, o28 / 4.0)
    gmv = o28 * 16.0
    return o7, o28, gmv


def feature_payload_high(tier: int, o90: int) -> dict[str, float]:
    o7, o28, gmv = orders_from_90d_high(o90)
    if tier == 0:
        return {
            "orders_7d": round(o7, 1),
            "orders_28d": round(o28, 1),
            "gmv_28d": round(gmv, 1),
            "orders_wow_change": -0.04,
            "gmv_mom_change": -0.03,
            "login_days_28d": 22.0,
            "support_tickets_28d": 2.0,
            "config_error_rate_28d": 0.01,
            "menu_sync_failures_28d": 0.0,
            "hours_zero_days_28d": 0.0,
            "peer_gmv_percentile": 68.0,
        }
    if tier == 1:
        return {
            "orders_7d": round(o7 * 0.95, 1),
            "orders_28d": round(o28 * 0.95, 1),
            "gmv_28d": round(gmv * 0.94, 1),
            "orders_wow_change": -0.17,
            "gmv_mom_change": -0.12,
            "login_days_28d": 16.0,
            "support_tickets_28d": 4.0,
            "config_error_rate_28d": 0.04,
            "menu_sync_failures_28d": 2.0,
            "hours_zero_days_28d": 1.0,
            "peer_gmv_percentile": 52.0,
        }
    if tier == 2:
        return {
            "orders_7d": round(o7 * 0.88, 1),
            "orders_28d": round(o28 * 0.88, 1),
            "gmv_28d": round(gmv * 0.85, 1),
            "orders_wow_change": -0.22,
            "gmv_mom_change": -0.21,
            "login_days_28d": 12.0,
            "support_tickets_28d": 5.0,
            "config_error_rate_28d": 0.06,
            "menu_sync_failures_28d": 4.0,
            "hours_zero_days_28d": 2.0,
            "peer_gmv_percentile": 22.0,
        }
    if tier == 3:
        return {
            "orders_7d": round(o7 * 0.72, 1),
            "orders_28d": round(o28 * 0.72, 1),
            "gmv_28d": round(gmv * 0.68, 1),
            "orders_wow_change": -0.32,
            "gmv_mom_change": -0.28,
            "login_days_28d": 8.0,
            "support_tickets_28d": 7.0,
            "config_error_rate_28d": 0.12,
            "menu_sync_failures_28d": 7.0,
            "hours_zero_days_28d": 5.0,
            "peer_gmv_percentile": 18.0,
        }
    return {
        "orders_7d": round(o7 * 0.35, 1),
        "orders_28d": round(o28 * 0.38, 1),
        "gmv_28d": round(gmv * 0.36, 1),
        "orders_wow_change": -0.52,
        "gmv_mom_change": -0.48,
        "login_days_28d": 3.0,
        "support_tickets_28d": 5.0,
        "config_error_rate_28d": 0.19,
        "menu_sync_failures_28d": 12.0,
        "hours_zero_days_28d": 9.0,
        "peer_gmv_percentile": 11.0,
    }


def feature_payload_low(tier: int, o90: int) -> dict[str, float]:
    """Bottom-quartile volumes: tiny absolute orders + weak peer position + tiered stress."""
    o28 = max(0.5, float(o90) * 28.0 / 90.0)
    o7 = max(0.2, o28 / 4.0)
    gmv = o28 * 20.0
    peer = 6.0 + tier * 3.5  # 6–20: far below ENT peers
    wow = -0.05 - tier * 0.12
    mom = -0.08 - tier * 0.09
    login = max(1.0, 14.0 - tier * 2.5)
    support = 1.0 + tier * 1.2
    cfg = 0.02 + tier * 0.035
    menu = float(min(10.0, tier * 2.2))
    hours = float(min(10.0, tier * 1.8))
    return {
        "orders_7d": round(o7, 2),
        "orders_28d": round(o28, 2),
        "gmv_28d": round(gmv, 1),
        "orders_wow_change": round(wow, 3),
        "gmv_mom_change": round(mom, 3),
        "login_days_28d": round(login, 1),
        "support_tickets_28d": round(support, 1),
        "config_error_rate_28d": round(min(0.22, cfg), 3),
        "menu_sync_failures_28d": menu,
        "hours_zero_days_28d": hours,
        "peer_gmv_percentile": peer,
    }


def load_split_demo_venues(path: Path) -> tuple[list[dict[str, str | int]], list[dict[str, str | int]]]:
    high: list[dict[str, str | int]] = []
    low: list[dict[str, str | int]] = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            row = {
                "venue_id": r["venue_id"].strip(),
                "country_code": r["country_code"].strip(),
                "market": r["market"].strip(),
                "orders_90d": int(r["orders_90d"]),
            }
            seg = r.get("volume_segment", "").strip()
            if seg == "high_volume_ent":
                high.append(row)
            elif seg == "low_volume_ent":
                low.append(row)
            else:
                raise SystemExit(f"{path}: unknown volume_segment {seg!r} for {row['venue_id']}")
    return high, low


def append_multi_surface_snapshots(
    snapshots: list[dict],
    high_rows: list[dict[str, str | int]],
    low_rows: list[dict[str, str | int]],
) -> None:
    """Add 2 extra product rows for many high venues and 2 for many low venues (multi-surface churn)."""
    seen = {(s["venue_id"], s["product"]) for s in snapshots}
    extra_high = ("wolt_plus", "takeaway_pickup")
    extra_low = ("drive", "wolt_for_work")

    for idx, row in enumerate(high_rows[:90]):
        tier = idx % 5
        feat = feature_payload_high(tier, int(row["orders_90d"]))
        for k, prod in enumerate(extra_high):
            if (row["venue_id"], prod) in seen:
                continue
            seen.add((row["venue_id"], prod))
            snapshots.append(
                {
                    "venue_id": row["venue_id"],
                    "merchant_id": None,
                    "market": row["market"],
                    "country_code": country_alpha3(str(row["country_code"])),
                    "product": prod,
                    "volume_segment": "high_volume_ent",
                    "orders_90d": row["orders_90d"],
                    "demo_venue_name": None,
                    "demo_risk_tier": tier,
                    "churn_reason_summary": (
                        f"[{prod}] "
                        + HIGH_CHURN_REASONS[(idx + k + tier) % len(HIGH_CHURN_REASONS)]
                    ),
                    "features": feat,
                }
            )

    for idx, row in enumerate(low_rows[:45]):
        tier = idx % 5
        feat = feature_payload_low(tier, int(row["orders_90d"]))
        for k, prod in enumerate(extra_low):
            if (row["venue_id"], prod) in seen:
                continue
            seen.add((row["venue_id"], prod))
            snapshots.append(
                {
                    "venue_id": row["venue_id"],
                    "merchant_id": None,
                    "market": row["market"],
                    "country_code": country_alpha3(str(row["country_code"])),
                    "product": prod,
                    "volume_segment": "low_volume_ent",
                    "orders_90d": row["orders_90d"],
                    "demo_venue_name": None,
                    "demo_risk_tier": tier,
                    "churn_reason_summary": (
                        f"[{prod}] "
                        + LOW_CHURN_REASONS[(idx + k + tier) % len(LOW_CHURN_REASONS)]
                    ),
                    "features": feat,
                }
            )


def main() -> None:
    if not DEMO_VENUES_CSV.is_file():
        raise SystemExit(f"Missing {DEMO_VENUES_CSV}")
    high_rows, low_rows = load_split_demo_venues(DEMO_VENUES_CSV)
    if len(high_rows) < 1 or len(low_rows) < 1:
        raise SystemExit(f"Need at least one high and one low row in {DEMO_VENUES_CSV}")

    snapshots: list[dict] = []

    for i, row in enumerate(high_rows):
        tier = i % 5
        product = PRODUCTS[i % len(PRODUCTS)]
        feat = feature_payload_high(tier, row["orders_90d"])
        snapshots.append(
            {
                "venue_id": row["venue_id"],
                "merchant_id": None,
                "market": row["market"],
                "country_code": country_alpha3(str(row["country_code"])),
                "product": product,
                "volume_segment": "high_volume_ent",
                "orders_90d": row["orders_90d"],
                "demo_venue_name": None,
                "demo_risk_tier": tier,
                "churn_reason_summary": HIGH_CHURN_REASONS[(i + tier) % len(HIGH_CHURN_REASONS)],
                "features": feat,
            }
        )

    base = len(snapshots)
    for j, row in enumerate(low_rows):
        tier = j % 5
        product = PRODUCTS[(base + j) % len(PRODUCTS)]
        feat = feature_payload_low(tier, row["orders_90d"])
        snapshots.append(
            {
                "venue_id": row["venue_id"],
                "merchant_id": None,
                "market": row["market"],
                "country_code": country_alpha3(str(row["country_code"])),
                "product": product,
                "volume_segment": "low_volume_ent",
                "orders_90d": row["orders_90d"],
                "demo_venue_name": None,
                "demo_risk_tier": tier,
                "churn_reason_summary": LOW_CHURN_REASONS[(j + tier) % len(LOW_CHURN_REASONS)],
                "features": feat,
            }
        )

    n_base = len(snapshots)
    append_multi_surface_snapshots(snapshots, high_rows, low_rows)
    n_extra = len(snapshots) - n_base

    out = {
        "source": "data/demo_venues.csv — ENT venues (high + low volume); AskWoltAI MCP for original rows.",
        "notes": (
            f"{n_base} base rows (one per CSV row) + {n_extra} multi-surface rows "
            "(same venue_id, extra product surfaces for UI / dry-run grouping tests). "
            "high_volume_ent: top cohort; low_volume_ent: bottom-quartile ENT. "
            "Brands: demo_venues.csv / venue_enrichment.json."
        ),
        "snapshots": snapshots,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {len(snapshots)} snapshots to {OUT_PATH}")


if __name__ == "__main__":
    main()
