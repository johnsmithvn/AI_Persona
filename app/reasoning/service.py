"""
ReasoningService — The orchestrator.

Flow:
  1. Call RetrievalService → get relevant memories
  2. Apply TokenGuard → trim to budget
  3. ModeController → get instruction + policy
  4. Epistemic boundary decision (mode-based: EXPAND only)
  5. PromptBuilder → build 4-part prompt
  6. LLMAdapter.generate() → get response
  7. Log to reasoning_logs
  8. Return QueryResponse

NEVER queries DB directly.
NEVER knows about embedding details.
"""

import hashlib
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.personality import build_system_prompt, load_personality
from app.core.token_guard import TokenGuard
from app.db.models import ReasoningLog
from app.llm.adapter import LLMAdapter, LLMConfig
from app.llm.embedding_adapter import EmbeddingAdapter
from app.logging.logger import logger
from app.reasoning.mode_controller import ModeController
from app.reasoning.prompt_builder import PromptBuilder
from app.retrieval.search import RetrievalService, SearchFilters
from app.schemas.query import QueryRequest, QueryResponse


class ReasoningService:
    """Orchestrates retrieval → mode → prompt → LLM → log."""

    def __init__(
        self,
        session: AsyncSession,
        llm_adapter: LLMAdapter,
        embedding_adapter: EmbeddingAdapter,
    ) -> None:
        self._session = session
        self._llm = llm_adapter
        self._retrieval = RetrievalService(session, embedding_adapter)
        self._mode_ctrl = ModeController()
        self._prompt_builder = PromptBuilder()
        self._token_guard = TokenGuard(token_counter=llm_adapter.count_tokens)

    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """Full reasoning pipeline. Returns QueryResponse."""
        start_time = time.monotonic()
        mode = request.mode.value  # ModeEnum → str

        # 1. Retrieve relevant memories
        filters = SearchFilters(
            content_type=request.content_type,
            threshold=request.threshold,
            limit=30,
            mode=mode,
        )
        memories = await self._retrieval.search(request.query, filters)

        # 2. Apply token budget
        budgeted = self._token_guard.check_budget(memories)

        # 3. Mode instruction + policy
        mode_instruction = self._mode_ctrl.get_instruction(mode)
        policy = self._mode_ctrl.get_policy(mode)

        # 4. Epistemic boundary — V1.1 Rule (5-Mode):
        #    EXPAND is the ONLY mode that allows external knowledge.
        #    All other modes: external_knowledge_used = False.
        #    Clean. No conditional threshold. Mode = permission.
        external_knowledge_used = policy.can_use_external_knowledge

        # 5. Load personality and build prompt
        personality = load_personality()
        system_prompt = build_system_prompt(personality)
        full_prompt = self._prompt_builder.build(
            system_prompt=system_prompt,
            mode_instruction=mode_instruction,
            memories=budgeted,
            user_query=request.query,
            external_knowledge_used=external_knowledge_used,
        )

        # 6. Call LLM
        llm_response = await self._llm.generate(
            full_prompt,
            LLMConfig(temperature=0.3, max_tokens=1200),
        )

        latency_ms = int((time.monotonic() - start_time) * 1000)
        memory_ids = [uuid.UUID(m.id) for m in budgeted]

        # 7. Log to reasoning_logs
        prompt_hash = hashlib.sha256(full_prompt.encode()).hexdigest()
        log = ReasoningLog(
            user_query=request.query,
            mode=mode,
            memory_ids=memory_ids,
            prompt_hash=prompt_hash,
            debug_prompt=full_prompt if False else None,  # Only in DEBUG mode
            external_knowledge_used=external_knowledge_used,
            confidence_score=0.5,  # LLM self-assessment not implemented in V1
            response=llm_response.content,
            token_usage={
                "prompt_tokens": llm_response.prompt_tokens,
                "completion_tokens": llm_response.completion_tokens,
                "total": llm_response.total_tokens,
            },
            latency_ms=latency_ms,
        )
        self._session.add(log)
        await self._session.commit()

        logger.info(
            "reasoning_complete",
            extra={
                "mode": mode,
                "memory_count": len(budgeted),
                "external_knowledge": external_knowledge_used,
                "latency_ms": latency_ms,
                "tokens": llm_response.total_tokens,
            },
        )

        return QueryResponse(
            response=llm_response.content,
            mode=mode,
            memory_used=memory_ids,
            token_usage={
                "prompt_tokens": llm_response.prompt_tokens,
                "completion_tokens": llm_response.completion_tokens,
                "total": llm_response.total_tokens,
            },
            external_knowledge_used=external_knowledge_used,
            latency_ms=latency_ms,
        )
