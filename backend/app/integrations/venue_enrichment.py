"""Venue-level display fields (brand, city) keyed by venue_id.

Production: replace data/venue_enrichment.json with a Snowflake export (dim merchant / tier).
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _repo_data_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "venue_enrichment.json"


@lru_cache
def _load_enrichment() -> Dict[str, Dict[str, Any]]:
    path = _repo_data_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data.get("by_venue_id") or {}
        return {str(k): dict(v) for k, v in raw.items()}
    except (OSError, json.JSONDecodeError, TypeError) as e:
        logger.warning("venue_enrichment.json unreadable: %s", e)
        return {}


def enrichment_for_venue(venue_id: str) -> Dict[str, Any]:
    """Return brand_name, city, country_code when present."""
    return dict(_load_enrichment().get(venue_id, {}))


def clear_enrichment_cache() -> None:
    _load_enrichment.cache_clear()
