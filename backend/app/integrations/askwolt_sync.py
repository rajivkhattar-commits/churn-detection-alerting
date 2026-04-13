"""Git fetch/pull for the AskWoltAI MCP clone — keep schema.py in sync during development.

Uses the same idea as ask-wolt-mcp/updater.py but lives in this repo so CI and agents
can call it without importing the MCP package.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.integrations.wolt_schema import clear_schema_cache, resolve_askwolt_home

logger = logging.getLogger(__name__)


def _git_env() -> dict:
    return {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


def check_askwolt_clone_updates(repo: Optional[Path] = None) -> Dict[str, Any]:
    """
    git fetch + count commits on origin/main not in HEAD.

    Returns keys: ok, repo, behind (int or None), changelog (str or None), error (str or None).
    """
    home = repo or resolve_askwolt_home()
    out: Dict[str, Any] = {"repo": str(home), "behind": None, "changelog": None, "error": None}
    if not (home / ".git").exists():
        out["error"] = "not_a_git_repo"
        return out

    kw = {"cwd": str(home), "capture_output": True, "text": True, "env": _git_env(), "timeout": 15}
    try:
        subprocess.run(["git", "fetch", "--quiet"], **kw)
        r = subprocess.run(
            ["git", "rev-list", "HEAD..origin/main", "--count"],
            **kw,
        )
        if r.returncode != 0:
            out["error"] = r.stderr.strip() or "rev-list failed"
            return out
        behind = int(r.stdout.strip() or "0")
        out["behind"] = behind
        if behind > 0:
            log = subprocess.run(
                [
                    "git",
                    "log",
                    "HEAD..origin/main",
                    "--max-count=5",
                    "--format=- %s",
                ],
                **kw,
            )
            if log.returncode == 0 and log.stdout.strip():
                out["changelog"] = log.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
        out["error"] = str(e)
    return out


def pull_askwolt_clone(repo: Optional[Path] = None) -> Tuple[bool, str]:
    """git pull --ff-only and pip install -r requirements.txt in repo venv if present."""
    home = repo or resolve_askwolt_home()
    if not (home / ".git").exists():
        return False, f"Not a git repo: {home}"

    kw = {"cwd": str(home), "capture_output": True, "text": True, "env": _git_env(), "timeout": 60}
    try:
        pull = subprocess.run(["git", "pull", "--ff-only"], **kw)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, str(e)

    if pull.returncode != 0:
        return False, pull.stderr.strip() or "git pull failed"

    msg = pull.stdout.strip() or "ok"
    venv_pip = home / ".venv" / "bin" / "pip"
    pip_cmd = str(venv_pip) if venv_pip.is_file() else "pip"
    req = home / "requirements.txt"
    pip_note = ""
    if req.is_file():
        try:
            pr = subprocess.run(
                [pip_cmd, "install", "-r", str(req), "--quiet"],
                cwd=str(home),
                capture_output=True,
                text=True,
                timeout=120,
                env=_git_env(),
            )
            if pr.returncode != 0:
                pip_note = "\n⚠️ pip install had errors — run manually in the clone."
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pip_note = "\n⚠️ Could not run pip — install requirements manually."

    clear_schema_cache()
    return True, f"{msg}{pip_note}"


def log_update_status_if_dev() -> None:
    """If DEBUG=1, log whether the ask-wolt-mcp clone is behind origin."""
    if os.environ.get("DEBUG", "").lower() not in ("1", "true", "yes"):
        return
    st = check_askwolt_clone_updates()
    b = st.get("behind")
    if st.get("error"):
        logger.info("AskWolt MCP clone update check: %s (%s)", st["error"], st["repo"])
        return
    if b and b > 0:
        logger.warning(
            "AskWolt MCP clone is %s commits behind origin/main — run scripts/sync-askwolt-mcp.sh or POST /api/dev/askwolt-mcp/sync",
            b,
        )
    else:
        logger.info("AskWolt MCP clone up to date: %s", st["repo"])
