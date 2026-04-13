"""Unit tests for askwolt_sync git helpers (mocked)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.integrations.askwolt_sync import check_askwolt_clone_updates


def test_check_updates_counts_behind(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    monkeypatch.setenv("ASKWOLT_MCP_HOME", str(repo))

    def fake_run(cmd, **kw):
        m = MagicMock()
        m.returncode = 0
        cwd = kw.get("cwd") or ""
        if "fetch" in cmd:
            m.stdout = ""
        elif "rev-list" in cmd and "--count" in cmd:
            m.stdout = "3"
        elif "log" in cmd:
            m.stdout = "- a commit\n- b commit"
        else:
            m.stdout = ""
        return m

    with patch("app.integrations.askwolt_sync.subprocess.run", side_effect=fake_run):
        out = check_askwolt_clone_updates(repo)

    assert out["behind"] == 3
    assert out["changelog"] is not None


def test_check_not_git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASKWOLT_MCP_HOME", str(tmp_path))
    out = check_askwolt_clone_updates(tmp_path)
    assert out["error"] == "not_a_git_repo"
