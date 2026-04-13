"""Snowflake connectivity; no-op when credentials absent (local demo)."""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Sequence

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class SnowflakeClient:
    """Thin wrapper around snowflake-connector-python."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._conn = None
        self._connect_error: Optional[str] = None
        if self._is_configured():
            self._connect()

    def _is_configured(self) -> bool:
        s = self._settings
        return bool(s.snowflake_account and s.snowflake_user and s.snowflake_password)

    def _connect(self) -> None:
        try:
            import snowflake.connector  # type: ignore

            s = self._settings
            self._conn = snowflake.connector.connect(
                account=s.snowflake_account,
                user=s.snowflake_user,
                password=s.snowflake_password,
                warehouse=s.snowflake_warehouse,
                database=s.snowflake_database,
                schema=s.snowflake_schema,
                role=s.snowflake_role,
            )
        except Exception as e:
            self._connect_error = str(e)
            logger.error("Snowflake connect failed: %s", e)
            self._conn = None

    @property
    def available(self) -> bool:
        return self._conn is not None

    @property
    def connect_error(self) -> Optional[str]:
        return self._connect_error

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:
        if not self._conn:
            raise RuntimeError("Snowflake not configured or connection failed")
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params or ())
        finally:
            cur.close()

    def fetch_all(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[tuple]:
        if not self._conn:
            raise RuntimeError("Snowflake not configured or connection failed")
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params or ())
            return cur.fetchall()
        finally:
            cur.close()

    def fetch_dicts(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[dict]:
        if not self._conn:
            raise RuntimeError("Snowflake not configured or connection failed")
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params or ())
            cols = [c[0].lower() for c in cur.description] if cur.description else []
            rows = cur.fetchall()
            return [dict(zip(cols, r)) for r in rows]
        finally:
            cur.close()


def get_snowflake_client() -> SnowflakeClient:
    return SnowflakeClient(get_settings())
