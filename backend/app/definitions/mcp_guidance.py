"""Static guidance for Cursor MCP servers (AskWoltAI + Snowflake) — no runtime MCP calls.

When definitions/joins are missing, the API surfaces this so humans and agents know
which MCP tools populate ENTERPRISE_DEFINITION_JSON and CANONICAL_JOINS_JSON.
"""

from __future__ import annotations

from typing import Any, Dict


def mcp_guidance() -> Dict[str, Any]:
    """Structured copy for /api/definitions/enterprise and docs."""
    return {
        "cursor_mcp_servers": {
            "askwoltai": {
                "purpose": "Wolt-aware natural language and schema discovery on PRODUCTION.",
                "tools": {
                    "get_schema": "Returns Snowflake schema reference text — use first to align sql/*.sql placeholders.",
                    "ask_wolt": "Ask how Enterprise (ENT) venues are defined, active counts, churn signals, etc.",
                    "run_wolt_sql": "Run a read-only SELECT you have already written (validation).",
                },
            },
            "snowflake": {
                "purpose": "Direct SQL against Snowflake (npx snowflake-mcp) — cross-check columns and joins.",
            },
        },
        "env_vars_to_populate": [
            "ASKWOLT_MCP_HOME — path to cloned ask-wolt-mcp repo (production: same schema.py as MCP; no MCP process required).",
            "DEBUG=true — enables startup clone-behind check and /api/dev/askwolt-mcp* during development.",
            "ENTERPRISE_DEFINITION_JSON — optional ENT merchant/venue prose for UI and LLM context.",
            "CANONICAL_JOINS_JSON — optional JSON override on top of schema.py for deployment-specific joins.",
        ],
        "dev_sync_script": "scripts/sync-askwolt-mcp.sh",
        "this_api_policy": "Read-only Snowflake from this service; no INSERT/DELETE. Feature SQL belongs in analytics/dbt or SELECT-only loaders.",
    }


def canonical_joins_hint_with_mcp() -> str:
    """Short hint when schema.py is unavailable and joins env is unset."""
    return (
        "Set ASKWOLT_MCP_HOME to your ask-wolt-mcp clone so schema.py (SCHEMA_DESCRIPTION) loads — "
        "that is the canonical join/table reference (same content AskWoltAI MCP exposes via get_schema). "
        "Optional: CANONICAL_JOINS_JSON for extra structured overrides. "
        "Use Cursor MCP only for discovery; production does not run MCP."
    )
