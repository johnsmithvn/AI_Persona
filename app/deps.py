"""
Dependency injection providers for FastAPI.
All resource creation is centralized here for easy swapping.

LLM_PROVIDER controls which adapters are used:
  "openai"   → OpenAI API (default)
  "lmstudio" → LM Studio local model (OpenAI-compatible)
"""

from functools import lru_cache

from app.config import get_settings
from app.llm.adapter import LLMAdapter
from app.llm.embedding_adapter import EmbeddingAdapter
from app.logging.logger import logger

settings = get_settings()


@lru_cache(maxsize=1)
def get_llm_adapter() -> LLMAdapter:
    """Singleton LLM adapter — selected by LLM_PROVIDER setting."""
    if settings.llm_provider == "lmstudio":
        from app.llm.lmstudio_adapter import LMStudioAdapter
        logger.info("llm_provider_init", extra={"provider": "lmstudio", "model": settings.llm_model})
        return LMStudioAdapter()
    else:
        from app.llm.openai_adapter import OpenAIAdapter
        logger.info("llm_provider_init", extra={"provider": "openai", "model": settings.llm_model})
        return OpenAIAdapter()


@lru_cache(maxsize=1)
def get_embedding_adapter() -> EmbeddingAdapter:
    """Singleton embedding adapter — selected by LLM_PROVIDER setting."""
    if settings.llm_provider == "lmstudio":
        from app.llm.lmstudio_embedding_adapter import LMStudioEmbeddingAdapter
        logger.info("embedding_provider_init", extra={"provider": "lmstudio", "model": settings.embedding_model})
        return LMStudioEmbeddingAdapter()
    else:
        from app.llm.openai_embedding_adapter import OpenAIEmbeddingAdapter
        logger.info("embedding_provider_init", extra={"provider": "openai", "model": settings.embedding_model})
        return OpenAIEmbeddingAdapter()
