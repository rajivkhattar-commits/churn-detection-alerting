"""Application settings from environment."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "churn-detection-api"
    debug: bool = False
    # "development" | "production" — controls outreach recipient routing (see outreach_routing).
    environment: str = "development"
    # Required for non–dry-run email sends when environment != production (your inbox only).
    outreach_dev_email: Optional[str] = None

    # Definitions: env | mcp — both resolve to ENTERPRISE_DEFINITION_JSON + CANONICAL_JOINS_JSON in practice.
    definitions_source: str = "env"

    # Snowflake: read-only (SELECT). This app never sends INSERT, UPDATE, DELETE, or DDL to Snowflake.
    snowflake_account: Optional[str] = None
    snowflake_user: Optional[str] = None
    snowflake_password: Optional[str] = None
    snowflake_warehouse: Optional[str] = None
    snowflake_database: Optional[str] = None
    snowflake_schema: str = "CHURN_APP"
    snowflake_role: Optional[str] = None

    # LLM: OpenAI-compatible API (IT sets base URL for Azure / internal gateway)
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None

    # Slack
    slack_bot_token: Optional[str] = None

    # Email (SMTP)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def effective_llm_api_key(settings: Settings) -> Optional[str]:
    return settings.llm_api_key or settings.openai_api_key


def effective_llm_model(settings: Settings) -> str:
    return settings.openai_model or settings.llm_model
