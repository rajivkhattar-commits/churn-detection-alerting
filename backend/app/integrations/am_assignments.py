"""Account manager email by brand × country (demo: JSON; production: replace with warehouse export)."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _repo_data_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "am_assignments.json"


@lru_cache
def _load() -> Dict[str, Any]:
    path = _repo_data_path()
    if not path.is_file():
        return {"by_brand_country": {}, "default_account_manager_email": None}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as e:
        logger.warning("am_assignments.json unreadable: %s", e)
        return {"by_brand_country": {}, "default_account_manager_email": None}


def clear_am_assignments_cache() -> None:
    _load.cache_clear()


def _norm_key(brand: str, country: str) -> str:
    return f"{brand.strip().lower()}|{country.strip().upper()}"


def resolve_account_manager_email(
    brand_name: Optional[str],
    country_code: Optional[str],
) -> Optional[str]:
    """Return AM email for brand in country, or default_account_manager_email, or None."""
    data = _load()
    default = data.get("default_account_manager_email")
    if isinstance(default, str) and default.strip():
        fallback = default.strip()
    else:
        fallback = None

    if not brand_name or not country_code:
        return fallback

    key = _norm_key(brand_name, country_code)
    m = data.get("by_brand_country", {}).get(key)
    if isinstance(m, dict):
        em = m.get("email")
        if isinstance(em, str) and em.strip():
            return em.strip()
    return fallback
