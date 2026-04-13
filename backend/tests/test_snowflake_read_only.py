"""Snowflake client is for reads only — no writeback module."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_diagnostics_states_no_snowflake_dml() -> None:
    r = client.get("/api/diagnostics/snowflake")
    assert r.status_code == 200
    data = r.json()
    assert data["snowflake_dml_policy"] == "disabled"
    assert "INSERT" in data["note"]


def test_definitions_endpoint_includes_mcp_guidance() -> None:
    r = client.get("/api/definitions/enterprise")
    assert r.status_code == 200
    data = r.json()
    assert "mcp" in data
    assert "askwoltai" in data["mcp"]["cursor_mcp_servers"]


def test_ui_copy_endpoint() -> None:
    r = client.get("/api/ui/copy")
    assert r.status_code == 200
    data = r.json()
    assert "classic" in data["product_labels"]
    assert "score_meaning" in data
