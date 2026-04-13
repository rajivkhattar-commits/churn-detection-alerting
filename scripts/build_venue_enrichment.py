#!/usr/bin/env python3
"""Build data/venue_enrichment.json from data/demo_venues.csv.

Single source of truth for demo venue_id, geo, volume_segment, and brand_name (Snowflake
D_VENUES–aligned names from AskWoltAI MCP when refreshed). Regenerate JSON after editing the CSV.

Run: python3 scripts/build_venue_enrichment.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEMO_VENUES_CSV = REPO / "data" / "demo_venues.csv"
OUT_PATH = REPO / "data" / "venue_enrichment.json"


def country_alpha3(raw: str) -> str:
    """Normalize to ISO 3166-1 alpha-3 (MCP / Snowflake venue lists use 3-letter codes)."""
    return raw.strip().upper()


def main() -> None:
    if not DEMO_VENUES_CSV.is_file():
        raise SystemExit(f"Missing {DEMO_VENUES_CSV}")
    by_id: dict[str, dict[str, str | None]] = {}
    with DEMO_VENUES_CSV.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            vid = r["venue_id"].strip()
            bn = (r.get("brand_name") or "").strip()
            seg = r.get("volume_segment", "").strip()
            if seg not in ("high_volume_ent", "low_volume_ent"):
                raise SystemExit(f"Unknown volume_segment {seg!r} for {vid}")
            by_id[vid] = {
                "brand_name": bn or None,
                "city": r["market"].strip(),
                "country_code": country_alpha3(r["country_code"]),
                "volume_segment": seg,
            }

    out = {
        "source": "data/demo_venues.csv — demo ENT list with brands (MCP/Snowflake-backed where refreshed).",
        "by_venue_id": by_id,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {len(by_id)} venues to {OUT_PATH}")


if __name__ == "__main__":
    main()
