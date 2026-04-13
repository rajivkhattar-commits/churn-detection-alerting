#!/usr/bin/env python3
"""Run a read-only Snowflake SELECT to measure row counts (warehouse scale check).

This does **not** load data into the churn app — the API still uses in-memory JSON snapshots.
Use this to sanity-check how large a full mart pull would be (e.g. ~1500 ENT venues × N products).

Setup:
  - Copy backend/.env.example to backend/.env and set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER,
    SNOWFLAKE_PASSWORD, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA (and role if needed).

Usage (from repo root):

  python3 scripts/snowflake_rowcount_probe.py

  # Custom SQL file (single statement returning one number in first column of first row):
  SNOWFLAKE_PROBE_SQL_FILE=sql/ent_venue_product_count_example.sql python3 scripts/snowflake_rowcount_probe.py

Default query: ``SELECT 1 AS ok`` — verifies connectivity only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKEND_ENV = REPO / "backend" / ".env"


def _load_dotenv() -> None:
    """Set os.environ from backend/.env without requiring python-dotenv."""
    if not BACKEND_ENV.is_file():
        return
    for line in BACKEND_ENV.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def main() -> None:
    _load_dotenv()
    account = os.environ.get("SNOWFLAKE_ACCOUNT")
    user = os.environ.get("SNOWFLAKE_USER")
    password = os.environ.get("SNOWFLAKE_PASSWORD")
    warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE")
    database = os.environ.get("SNOWFLAKE_DATABASE")
    schema = os.environ.get("SNOWFLAKE_SCHEMA", "CHURN_APP")
    role = os.environ.get("SNOWFLAKE_ROLE")

    if not all([account, user, password]):
        print(
            "Snowflake credentials not set. Add SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD "
            f"to {BACKEND_ENV} (see backend/.env.example).",
            file=sys.stderr,
        )
        sys.exit(2)

    sql_path = os.environ.get("SNOWFLAKE_PROBE_SQL_FILE")
    if sql_path:
        p = Path(sql_path)
        if not p.is_file():
            print(f"SQL file not found: {p}", file=sys.stderr)
            sys.exit(1)
        raw = p.read_text(encoding="utf-8")
        lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("--")]
        sql = "\n".join(lines).strip()
        if not sql:
            print("No non-comment SQL in file.", file=sys.stderr)
            sys.exit(1)
    else:
        sql = "SELECT 1 AS ok"

    try:
        import snowflake.connector
    except ImportError:
        print("Install snowflake-connector-python in the backend venv.", file=sys.stderr)
        sys.exit(1)

    kwargs = {
        "account": account,
        "user": user,
        "password": password,
        "warehouse": warehouse,
        "database": database,
        "schema": schema,
    }
    if role:
        kwargs["role"] = role

    print("Connecting…", flush=True)
    conn = snowflake.connector.connect(**kwargs)
    try:
        cur = conn.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [c[0] for c in (cur.description or [])]
            print("Columns:", cols)
            print("First row(s):", rows[:5])
            print("Row count returned:", len(rows))
        finally:
            cur.close()
    finally:
        conn.close()
    print("Done (read-only).")


if __name__ == "__main__":
    main()
