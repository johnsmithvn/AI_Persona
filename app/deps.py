"""
Dependency injection providers for FastAPI.
All resource creation is centralized here for easy swapping in tests.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db
from app.llm.adapter import LLMAdapter
from app.llm.embedding_adapter import EmbeddingAdapter
from app.llm.openai_adapter import OpenAIAdapter
from app.llm.openai_embedding_adapter import OpenAIEmbeddingAdapter


@lru_cache(maxsize=1)
def get_llm_adapter() -> LLMAdapter:
    """Singleton LLM adapter — shared across requests."""
    return OpenAIAdapter()


@lru_cache(maxsize=1)
def get_embedding_adapter() -> EmbeddingAdapter:
    """Singleton embedding adapter — shared across requests."""
    return OpenAIEmbeddingAdapter()
