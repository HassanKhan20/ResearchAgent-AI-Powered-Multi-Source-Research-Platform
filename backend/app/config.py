from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ResearchAgent"
    # Falls back to a local SQLite file so the API runs without Postgres.
    database_url: str = "sqlite+aiosqlite:///./research.db"
    # Leave empty to use the in-process cache instead of Redis.
    redis_url: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-5-5"
    llm_effort: str = "medium"

    tavily_api_key: str = ""
    # When true, search providers return deterministic fixtures (used in tests / offline demos).
    offline_mode: bool = False

    max_sources: int = 12
    max_sub_queries: int = 4
    max_refine_rounds: int = 1
    search_cache_ttl: int = 60 * 60 * 6
    session_ttl: int = 60 * 60 * 24 * 7

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
