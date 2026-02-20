"""
OpenAI EmbeddingAdapter implementation.
Uses text-embedding-3-small by default (configurable via EMBEDDING_MODEL env var).
"""

from openai import AsyncOpenAI

from app.config import get_settings
from app.exceptions.handlers import EmbeddingFailedError
from app.llm.embedding_adapter import EmbeddingAdapter
from app.logging.logger import logger

settings = get_settings()


class OpenAIEmbeddingAdapter(EmbeddingAdapter):

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.embedding_model
        self._dimension = settings.embedding_dimension

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        """Embed a single text. Raises EmbeddingFailedError on failure."""
        try:
            response = await self._client.embeddings.create(
                input=text,
                model=self._model,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.error("embedding_failed", extra={"error": str(exc)})
            raise EmbeddingFailedError(str(exc)) from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call."""
        if not texts:
            return []
        try:
            response = await self._client.embeddings.create(
                input=texts,
                model=self._model,
            )
            # API returns results in the same order as inputs
            return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        except Exception as exc:
            logger.error("batch_embedding_failed", extra={"error": str(exc), "batch_size": len(texts)})
            raise EmbeddingFailedError(str(exc)) from exc
