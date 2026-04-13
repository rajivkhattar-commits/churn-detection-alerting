"""Pytest configuration."""

import sys
from pathlib import Path

# Ensure `app` package is importable when running from repo root or backend/
backend = Path(__file__).resolve().parent.parent
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))
