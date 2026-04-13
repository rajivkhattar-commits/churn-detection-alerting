"""Definition providers: env vs MCP source; canonical joins env."""

import json
import os

import pytest

from app.config import get_settings
from app.definitions.mcp_guidance import mcp_guidance
from app.definitions.provider import (
    EnvDefinitionProvider,
    McpDefinitionProvider,
    canonical_joins_from_env,
    clear_definition_cache,
)
from app.integrations.wolt_schema import clear_schema_cache


def test_default_enterprise_definition_from_repo_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENTERPRISE_DEFINITION_JSON", raising=False)
    p = EnvDefinitionProvider()
    assert "Classic" in p.enterprise_definition_text() or "classic" in p.enterprise_definition_text().lower()
    meta = p.enterprise_metadata()
    assert meta.get("source") == "repo_data"
    assert meta.get("has_json") is True
    parsed = meta.get("parsed") or {}
    assert "product_surfaces" in parsed
    assert "wolt_plus" in parsed["product_surfaces"]


def test_env_definition_json_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"text": "Enterprise = test flag", "version": 1}
    monkeypatch.setenv("ENTERPRISE_DEFINITION_JSON", json.dumps(payload))
    p = EnvDefinitionProvider()
    assert "test flag" in p.enterprise_definition_text()
    meta = p.enterprise_metadata()
    assert meta["source"] == "env"
    assert meta["parsed"]["version"] == 1


def test_mcp_falls_back_to_env_when_no_sync_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("DEFINITIONS_MCP_SYNC_PATH", raising=False)
    monkeypatch.setenv("ENTERPRISE_DEFINITION_JSON", json.dumps({"text": "from env fallback"}))
    p = McpDefinitionProvider()
    assert "from env fallback" in p.enterprise_definition_text()


def test_mcp_sync_file_priority(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    f = tmp_path / "mcp.json"
    f.write_text(json.dumps({"text": "from file"}), encoding="utf-8")
    monkeypatch.setenv("DEFINITIONS_MCP_SYNC_PATH", str(f))
    p = McpDefinitionProvider()
    assert p.enterprise_definition_text() == "from file"


def test_get_definition_provider_respects_definitions_source(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.definitions.provider import get_definition_provider

    monkeypatch.setenv("DEFINITIONS_SOURCE", "mcp")
    monkeypatch.setenv("ENTERPRISE_DEFINITION_JSON", json.dumps({"text": "mcp mode"}))
    get_settings.cache_clear()
    clear_definition_cache()
    p = get_definition_provider()
    assert p.enterprise_metadata()["source"] == "mcp"


def test_canonical_joins_json(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ASKWOLT_MCP_HOME", str(tmp_path))
    clear_schema_cache()
    monkeypatch.setenv(
        "CANONICAL_JOINS_JSON",
        json.dumps({"venue": {"to_orders": "orders.venue_id = venue.id"}}),
    )
    cj = canonical_joins_from_env()
    assert cj["configured"] is True
    assert cj["primary_source"] == "CANONICAL_JOINS_JSON"
    assert "venue" in cj["joins"]


def test_canonical_joins_missing(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ASKWOLT_MCP_HOME", str(tmp_path))
    monkeypatch.delenv("CANONICAL_JOINS_JSON", raising=False)
    clear_schema_cache()
    cj = canonical_joins_from_env()
    assert cj["configured"] is False
    assert "ASKWOLT_MCP_HOME" in cj["hint"] or "ask-wolt-mcp" in cj["hint"]


def test_schema_py_loads_when_clone_present(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    home = Path.home() / "ask-wolt-mcp"
    if not (home / "schema.py").is_file():
        pytest.skip("No ask-wolt-mcp clone at ~/ask-wolt-mcp")
    clear_schema_cache()
    monkeypatch.delenv("CANONICAL_JOINS_JSON", raising=False)
    cj = canonical_joins_from_env()
    assert cj["configured"] is True
    assert cj["primary_source"] == "askwolt_schema_py"
    assert cj["schema_reference"]["available"] is True
    assert cj["schema_reference"]["schema_description_chars"] > 1000


def test_mcp_guidance_has_cursor_tools() -> None:
    g = mcp_guidance()
    assert "askwoltai" in g["cursor_mcp_servers"]
    assert "get_schema" in g["cursor_mcp_servers"]["askwoltai"]["tools"]
