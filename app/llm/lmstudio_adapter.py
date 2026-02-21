"""
LM Studio LLMAdapter — OpenAI-compatible local model via LM Studio.

LM Studio serves at http://localhost:1234/v1 by default.
Uses the same openai SDK with base_url override — zero new dependencies.
"""

from typing import Optional

import tiktoken
from openai import AsyncOpenAI

from app.config import get_settings
from app.exceptions.handlers import LLMError, LLMTimeoutError
from app.llm.adapter import LLMAdapter, LLMConfig, LLMResponse
from app.logging.logger import logger

settings = get_settings()


class LMStudioAdapter(LLMAdapter):

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.lmstudio_base_url,
            api_key="lm-studio",  # LM Studio ignores this but SDK requires it
        )
        self._model = settings.llm_model
        # LM Studio models won't have tiktoken encodings — use cl100k_base as proxy
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

            # LM Studio may return None for usage on some models
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            return LLMResponse(
                content=choice.message.content or "",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                model=self._model,
            )
        except TimeoutError as exc:
            raise LLMTimeoutError() from exc
        except Exception as exc:
            logger.error("llm_request_failed", extra={"error": str(exc), "model": self._model, "provider": "lmstudio"})
            raise LLMError(str(exc)) from exc

    def count_tokens(self, text: str) -> int:
        return len(self._encoding.encode(text))
