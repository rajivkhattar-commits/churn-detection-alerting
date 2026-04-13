"""Debug-only AskWolt clone status/sync endpoints."""

from unittest.mock import patch

from app.config import get_settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_dev_askwolt_404_when_debug_off(monkeypatch) -> None:
    monkeypatch.delenv("DEBUG", raising=False)
    get_settings.cache_clear()
    r = client.get("/api/dev/askwolt-mcp")
    assert r.status_code == 404


def test_dev_askwolt_status_when_debug_on(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG", "true")
    get_settings.cache_clear()
    fake = {"repo": "/tmp", "behind": 0, "changelog": None, "error": None}
    with patch("app.main.check_askwolt_clone_updates", return_value=fake):
        r = client.get("/api/dev/askwolt-mcp")
    assert r.status_code == 200
    assert r.json() == fake
    get_settings.cache_clear()
    monkeypatch.delenv("DEBUG", raising=False)
    get_settings.cache_clear()


def test_dev_sync_when_debug_on(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG", "true")
    get_settings.cache_clear()
    with patch("app.main.pull_askwolt_clone", return_value=(True, "Already up to date")):
        r = client.post("/api/dev/askwolt-mcp/sync")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    get_settings.cache_clear()
    monkeypatch.delenv("DEBUG", raising=False)
    get_settings.cache_clear()
