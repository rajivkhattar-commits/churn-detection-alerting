#!/usr/bin/env bash
#
# Enterprise churn detection & alerting — run the FastAPI app locally with the
# project virtualenv. Opens the UI in your default browser (static build under
# backend/static from `npm run build` in frontend/).
#
# Usage:
#   ./scripts/start-churn-tool-local.sh
#   CHURN_DETECTION_ROOT=/path/to/churn-detection-alerting ./scripts/start-churn-tool-local.sh
#
# Rebuild the frontend into backend/static first (full UI: presets + dev-tagged slider, not strict):
#   CHURN_REBUILD_UI=1 ./scripts/start-churn-tool-local.sh
# Or manually: cd frontend && npm run build
# Strict production UI: cd frontend && VITE_STRICT_PROD=true npm run build
#

set -euo pipefail

ROOT="${CHURN_DETECTION_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
FRONTEND="$ROOT/frontend"
BACKEND="$ROOT/backend"
VENV_PY="$BACKEND/.venv/bin/python"
HOST="${CHURN_HOST:-127.0.0.1}"
PORT="${CHURN_PORT:-8000}"
URL="http://${HOST}:${PORT}/"

if [[ ! -d "$BACKEND" ]]; then
  echo "churn tool: backend directory not found: $BACKEND" >&2
  exit 1
fi

cd "$BACKEND"

if [[ ! -x "$VENV_PY" ]]; then
  echo "churn tool: Python venv missing. From the repo:" >&2
  echo "  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export PYTHONPATH=.
export DEBUG="${DEBUG:-true}"

if [[ "${CHURN_REBUILD_UI:-}" == "1" ]]; then
  if [[ ! -d "$FRONTEND" ]] || [[ ! -f "$FRONTEND/package.json" ]]; then
    echo "churn tool: frontend not found at $FRONTEND — skipping UI rebuild" >&2
  else
    echo "churn tool: rebuilding frontend → backend/static (default UI, VITE_STRICT_PROD unset)…"
    (cd "$FRONTEND" && npm run build)
    echo "churn tool: frontend build done."
    echo ""
  fi
fi

echo "churn tool: starting API at $URL (DEBUG=$DEBUG)"
echo "churn tool: repo root $ROOT"
echo ""

# Give uvicorn a moment to bind, then open the app (macOS).
if command -v open >/dev/null 2>&1; then
  (sleep 1 && open "$URL") &
else
  echo "churn tool: open this URL manually: $URL"
fi

exec "$VENV_PY" -m uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
