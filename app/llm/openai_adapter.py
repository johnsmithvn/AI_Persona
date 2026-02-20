"""
OpenAI LLMAdapter implementation.
Model is configurable via LLM_MODEL env var (default: gpt-4.1-mini).
"""

from typing import Optional

import tiktoken
from openai import AsyncOpenAI

from app.config import get_settings
from app.exceptions.handlers import LLMError, LLMTimeoutError
from app.llm.adapter import LLMAdapter, LLMConfig, LLMResponse
from app.logging.logger import logger

settings = get_settings()


class OpenAIAdapter(LLMAdapter):

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.llm_model
        # tiktoken encoding — use cl100k_base as fallback for newer models
        try:
            self._encoding = tiktoken.encoding_for_model(self._model)
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")

    async def generate(self, prompt: str, config: Optional[LLMConfig] = None) -> LLMResponse:
        cfg = config or LLMConfig()
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
            )
            choice = response.choices[0]
            usage = response.usage
            return LLMResponse(
                content=choice.message.content or "",
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                model=self._model,
            )
        except TimeoutError as exc:
            raise LLMTimeoutError() from exc
        except Exception as exc:
            logger.error("llm_request_failed", extra={"error": str(exc), "model": self._model})
            raise LLMError(str(exc)) from exc

    def count_tokens(self, text: str) -> int:
        return len(self._encoding.encode(text))
