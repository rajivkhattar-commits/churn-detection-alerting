#!/usr/bin/env bash
# Pull latest ask-wolt-mcp (same repo as AskWoltAI MCP) and refresh Python deps.
# Uses ASKWOLT_MCP_HOME or defaults to ~/ask-wolt-mcp

set -euo pipefail
REPO="${ASKWOLT_MCP_HOME:-$HOME/ask-wolt-mcp}"

if [[ ! -d "$REPO/.git" ]]; then
  echo "No git repo at $REPO — clone first:" >&2
  echo "  git clone https://github.com/rajivkhattar-commits/ask-wolt-mcp.git $REPO" >&2
  exit 1
fi

cd "$REPO"
git fetch --quiet
BEHIND=$(git rev-list HEAD..origin/main --count 2>/dev/null || echo 0)
if [[ "${BEHIND:-0}" -gt 0 ]]; then
  echo "Behind origin/main by $BEHIND commit(s); pulling..."
else
  echo "Already up to date with origin/main."
fi
git pull --ff-only

if [[ -x .venv/bin/pip ]]; then
  .venv/bin/pip install -r requirements.txt --quiet
  echo "pip install OK (.venv)"
elif command -v pip3 >/dev/null; then
  pip3 install -r requirements.txt --quiet
  echo "pip install OK (pip3)"
else
  echo "⚠️ No pip found — run pip install -r requirements.txt in $REPO" >&2
fi

echo "Done. Restart the churn API to reload schema (or rely on --reload)."
