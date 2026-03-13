"""Configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/satoic"
    memory_api_token: str = "changeme"
    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"
    display_timezone: str = "America/Toronto"
    max_recall_results: int = 20
    max_body_length: int = 50000
    registry_archive_root: str = "/var/lib/registry-archive"
    registry_fetch_timeout_seconds: float = 15.0
    registry_max_extract_chars: int = 20000

    model_config = SettingsConfigDict(env_prefix="MEMORY_")


settings = Settings()
