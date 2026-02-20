"""
Application configuration — single source of truth for all env vars.
Uses pydantic-settings for validation + auto-load from .env
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://ai_user:ai_password@localhost:5432/ai_person"

    # ─── OpenAI ───────────────────────────────────────────────────────────────
    openai_api_key: str = ""

    # ─── Embedding ────────────────────────────────────────────────────────────
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # ─── LLM ──────────────────────────────────────────────────────────────────
    llm_model: str = "gpt-4.1-mini"

    # ─── App ──────────────────────────────────────────────────────────────────
    max_context_tokens: int = 3000
    log_level: str = "INFO"
    debug: bool = False

    # ─── Worker ───────────────────────────────────────────────────────────────
    embedding_worker_interval_seconds: int = 5
    embedding_worker_batch_size: int = 10

    # ─── Retrieval ────────────────────────────────────────────────────────────
    retrieval_candidate_pool: int = 500
    retrieval_final_limit: int = 30
    retrieval_distance_threshold: float = 0.7

    # ─── Ranking weights ──────────────────────────────────────────────────────
    ranking_weight_semantic: float = 0.60
    ranking_weight_recency: float = 0.15
    ranking_weight_importance: float = 0.25
    ranking_recency_half_life_days: float = 30.0

    # ─── Diversity guard ──────────────────────────────────────────────────────
    diversity_cosine_threshold: float = 0.95


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
