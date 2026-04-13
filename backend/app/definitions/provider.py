"""Enterprise definitions and canonical joins.

**Canonical joins / tables:** loaded from AskWoltAI **`schema.py`** via **ASKWOLT_MCP_HOME**
(pointing at a clone of `ask-wolt-mcp`). That file’s `SCHEMA_DESCRIPTION` is the same source
AskWoltAI MCP uses at `get_schema` — production does not need MCP online.

Optional **CANONICAL_JOINS_JSON** overrides or extends structured join hints for your deployment.

**Enterprise prose:** **ENTERPRISE_DEFINITION_JSON** (still recommended for ENT merchant copy).

Cursor MCP remains useful for interactive discovery; the API only reads disk + env.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from app.config import Settings, get_settings
from app.definitions.mcp_guidance import canonical_joins_hint_with_mcp
from app.integrations.wolt_schema import load_askwolt_schema_reference

logger = logging.getLogger(__name__)


def _default_enterprise_definition_path() -> Path:
    """Repo `data/enterprise_churn_definition.json` (same directory layout as `data/churn_labels_example.csv`)."""
    return Path(__file__).resolve().parents[3] / "data" / "enterprise_churn_definition.json"


def _load_enterprise_json_file(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def canonical_joins_from_env() -> Dict[str, Any]:
    """Schema-backed joins (AskWoltAI `schema.py`) plus optional CANONICAL_JOINS_JSON override."""
    schema_ref = load_askwolt_schema_reference()
    raw = os.environ.get("CANONICAL_JOINS_JSON")
    out: Dict[str, Any] = {
        "schema_reference": schema_ref,
    }

    env_joins: Any = None
    if raw:
        try:
            env_joins = json.loads(raw)
            out["env_override"] = env_joins
        except json.JSONDecodeError as e:
            logger.error("CANONICAL_JOINS_JSON is not valid JSON: %s", e)
            out["env_error"] = {"invalid_json": True, "detail": str(e)}

    if env_joins is not None:
        out["configured"] = True
        out["primary_source"] = "CANONICAL_JOINS_JSON"
        out["joins"] = env_joins
    elif schema_ref.get("available"):
        out["configured"] = True
        out["primary_source"] = "askwolt_schema_py"
        out["joins"] = {
            "_documentation": (
                "Table grains and join patterns are in schema_reference.schema_description_excerpt "
                "(from ask-wolt-mcp/schema.py SCHEMA_DESCRIPTION). The excerpt is truncated — for churn analytics, "
                "open schema.py and search for 'CHURN / VENUE LIFECYCLE' and 'VENUE-LEVEL CHURN WITH REASONS' "
                "(MERCHANT reporting tables), or raise WOLT_SCHEMA_EXCERPT_CHARS with care for response size."
            ),
        }
    else:
        out["configured"] = False
        out["primary_source"] = "none"
        out["hint"] = canonical_joins_hint_with_mcp()

    return out


class DefinitionProvider(ABC):
    """Resolves business definitions used to build cohort SQL and UI copy."""

    @abstractmethod
    def enterprise_definition_text(self) -> str:
        """Human-readable definition (for prompts, docs, support)."""

    @abstractmethod
    def enterprise_metadata(self) -> Dict[str, Any]:
        """Structured metadata (version, source, optional SQL hints)."""


class EnvDefinitionProvider(DefinitionProvider):
    """Primary provider: ENTERPRISE_DEFINITION_JSON, else repo `data/enterprise_churn_definition.json`."""

    def enterprise_definition_text(self) -> str:
        raw = os.environ.get("ENTERPRISE_DEFINITION_JSON")
        if raw:
            try:
                data = json.loads(raw)
                return str(data.get("text") or data.get("definition") or raw)
            except json.JSONDecodeError:
                return raw
        path = _default_enterprise_definition_path()
        if path.is_file():
            try:
                data = _load_enterprise_json_file(path)
                return str(data.get("text") or data.get("definition") or "")
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Could not read default enterprise definition %s: %s", path, e)
        return (
            "Set ENTERPRISE_DEFINITION_JSON to the Enterprise venue definition. "
            "In Cursor, use AskWoltAI MCP (ask_wolt / get_schema), then paste the answer into this env var."
        )

    def enterprise_metadata(self) -> Dict[str, Any]:
        raw = os.environ.get("ENTERPRISE_DEFINITION_JSON")
        meta: Dict[str, Any] = {"source": "env", "has_json": bool(raw)}
        if raw:
            try:
                meta["parsed"] = json.loads(raw)
            except json.JSONDecodeError:
                meta["parsed"] = None
            return meta
        path = _default_enterprise_definition_path()
        if path.is_file():
            try:
                meta["parsed"] = _load_enterprise_json_file(path)
                meta["source"] = "repo_data"
                meta["path"] = str(path)
                meta["has_json"] = True
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Could not parse default enterprise definition %s: %s", path, e)
                meta["parsed"] = None
                meta["source"] = "repo_data_error"
        else:
            meta["source"] = "missing"
            meta["has_json"] = False
        return meta


class McpDefinitionProvider(DefinitionProvider):
    """Same as env: MCP content should land in ENTERPRISE_DEFINITION_JSON / CANONICAL_JOINS_JSON.

    Optional file DEFINITIONS_MCP_SYNC_PATH is still supported for local dev if you prefer a file drop.
    """

    def enterprise_definition_text(self) -> str:
        path = os.environ.get("DEFINITIONS_MCP_SYNC_PATH")
        if path and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                return str(data.get("text") or data.get("definition") or data)
            except (OSError, json.JSONDecodeError) as e:
                logger.error("Failed to read DEFINITIONS_MCP_SYNC_PATH %s: %s", path, e)
                raise RuntimeError(f"MCP definition sync file invalid: {path}") from e
        return EnvDefinitionProvider().enterprise_definition_text()

    def enterprise_metadata(self) -> Dict[str, Any]:
        base = EnvDefinitionProvider().enterprise_metadata()
        base.update(
            {
                "source": "mcp",
                "resource_uri": os.environ.get("DEFINITIONS_MCP_RESOURCE_URI"),
                "sync_path": os.environ.get("DEFINITIONS_MCP_SYNC_PATH"),
            }
        )
        return base


def _provider_for_settings(settings: Settings) -> DefinitionProvider:
    src = (settings.definitions_source or "env").lower()
    if src == "mcp":
        return McpDefinitionProvider()
    return EnvDefinitionProvider()


@lru_cache
def get_definition_provider() -> DefinitionProvider:
    return _provider_for_settings(get_settings())


def clear_definition_cache() -> None:
    get_definition_provider.cache_clear()
