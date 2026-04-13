"""Load canonical table/join documentation from AskWoltAI `schema.py` (no MCP at runtime).

Set **ASKWOLT_MCP_HOME** to the path of the cloned `ask-wolt-mcp` repo (contains `schema.py`
and `holiday_calendar.py`). Production uses this path on the API host — Cursor MCP is only
needed for interactive discovery, not for serving requests.

The authoritative join and table documentation is `SCHEMA_DESCRIPTION` in that file.
"""

from __future__ import annotations

import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_HOME = Path.home() / "ask-wolt-mcp"


def _resolve_home() -> Path:
    raw = os.environ.get("ASKWOLT_MCP_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(DEFAULT_HOME).resolve()


def resolve_askwolt_home() -> Path:
    """Public: path to ask-wolt-mcp clone (ASKWOLT_MCP_HOME or ~/ask-wolt-mcp)."""
    return _resolve_home()


@lru_cache(maxsize=8)
def _load_impl(home_resolved: str) -> Dict[str, Any]:
    home = Path(home_resolved)
    schema_file = home / "schema.py"
    if not schema_file.is_file():
        return {
            "available": False,
            "path_checked": str(home),
            "error": "schema.py not found",
            "hint": "Clone https://github.com/rajivkhattar-commits/ask-wolt-mcp and set ASKWOLT_MCP_HOME, "
            "or deploy the repo next to the API so joins stay aligned with AskWoltAI.",
        }

    root = str(home)
    if root not in sys.path:
        sys.path.insert(0, root)

    try:
        import schema as wolt_schema  # noqa: PLC0415

        desc = getattr(wolt_schema, "SCHEMA_DESCRIPTION", None) or ""
        excerpt_max = int(os.environ.get("WOLT_SCHEMA_EXCERPT_CHARS", "12000"))
        return {
            "available": True,
            "path": str(home),
            "source_module": "schema.SCHEMA_DESCRIPTION",
            "schema_description_chars": len(desc),
            "schema_description_excerpt": desc[:excerpt_max],
            "note": "Join paths and table grains are documented here; update the ask-wolt-mcp repo to refresh.",
        }
    except Exception as e:
        logger.exception("Failed to import AskWoltAI schema from %s", home)
        return {
            "available": False,
            "path_checked": str(home),
            "error": str(e),
            "hint": "Ensure ASKWOLT_MCP_HOME points to a full clone (needs holiday_calendar.py and schema.py).",
        }


def _dev_fallback_mcp_live() -> Dict[str, Any]:
    """When the local clone cannot supply schema.py, devs use Cursor AskWoltAI MCP for live schema."""
    return {
        "use_cursor_askwoltai_mcp": True,
        "tools": ["get_schema", "ask_wolt", "run_wolt_sql"],
        "hint": "Use AskWoltAI MCP in Cursor until ASKWOLT_MCP_HOME loads. Pull the clone with scripts/sync-askwolt-mcp.sh.",
    }


def load_askwolt_schema_reference() -> Dict[str, Any]:
    """Import `schema` from the AskWoltAI MCP checkout and return SCHEMA_DESCRIPTION metadata."""
    d = dict(_load_impl(str(_resolve_home())))
    if not d.get("available"):
        d["dev_fallback"] = _dev_fallback_mcp_live()
    return d


def clear_schema_cache() -> None:
    _load_impl.cache_clear()
