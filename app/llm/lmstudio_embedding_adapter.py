"""
LM Studio EmbeddingAdapter — OpenAI-compatible local embedding via LM Studio.

LM Studio serves embeddings at the same base URL as chat completions.
Uses the same openai SDK with base_url override.

NOTE: You must load an embedding model in LM Studio separately from the chat model.
      Embedding dimension must match EMBEDDING_DIMENSION in .env (default 1536).
"""

from openai import AsyncOpenAI

from app.config import get_settings
from app.exceptions.handlers import EmbeddingFailedError
from app.llm.embedding_adapter import EmbeddingAdapter
from app.logging.logger import logger

settings = get_settings()


class LMStudioEmbeddingAdapter(EmbeddingAdapter):

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.lmstudio_base_url,
            api_key="lm-studio",  # LM Studio ignores this but SDK requires it
        )
        self._model = settings.embedding_model
        self._dimension = settings.embedding_dimension

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        """Embed a single text via LM Studio. Raises EmbeddingFailedError on failure."""
        try:
            response = await self._client.embeddings.create(
                input=text,
                model=self._model,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.error("embedding_failed", extra={"error": str(exc), "provider": "lmstudio"})
            raise EmbeddingFailedError(str(exc)) from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts via LM Studio."""
        if not texts:
            return []
        try:
            response = await self._client.embeddings.create(
                input=texts,
                model=self._model,
            )
            return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        except Exception as exc:
            logger.error("batch_embedding_failed", extra={"error": str(exc), "batch_size": len(texts), "provider": "lmstudio"})
            raise EmbeddingFailedError(str(exc)) from exc
