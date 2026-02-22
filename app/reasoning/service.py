"""
ReasoningService — The orchestrator.

Flow:
  1. Call RetrievalService → get relevant memories
  2. Apply TokenGuard → trim to budget
  3. ModeController → get instruction + policy
  4. Epistemic boundary decision (mode-based: EXPAND only)
  5. PromptBuilder → build 4-part prompt
  6. LLMAdapter.generate() → get response
  7. Validate citations (P0 — enforce must_cite_memory_id)
  8. Log to reasoning_logs
  9. Return QueryResponse

NEVER queries DB directly.
NEVER knows about embedding details.
"""

import json
import hashlib
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.personality import build_system_prompt, load_personality
from app.core.prompts import ModePolicy
from app.core.token_guard import BudgetedMemory, TokenGuard
from app.db.models import ReasoningLog
from app.llm.adapter import LLMAdapter, LLMConfig
from app.llm.embedding_adapter import EmbeddingAdapter
from app.logging.logger import logger
from app.exceptions.handlers import PolicyViolationError
from app.reasoning.mode_controller import ModeController
from app.reasoning.prompt_builder import PromptBuilder
from app.retrieval.relevance_gate import apply_relevance_gate
from app.retrieval.search import RetrievalService, SearchFilters
from app.schemas.query import QueryRequest, QueryResponse

# Regex to find [Memory N] citations in LLM response
_CITATION_PATTERN = re.compile(r"\[Memory\s+(\d+)\]")
_RERANK_JSON_PATTERN = re.compile(r"\{[\s\S]*?\}|\[[\s\S]*?\]")


class ReasoningService:
    """Orchestrates retrieval → mode → prompt → LLM → validate → log."""

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

        # 1.1 Relevance gate — strict filtering to avoid near-near noise.
        memories, gate_decision = apply_relevance_gate(memories, mode)
        logger.info("relevance_gate_applied", extra=gate_decision.to_log())

        # 2. Apply token budget
        budgeted = self._token_guard.check_budget(memories)

        # Recall modes: if no memory survives retrieval+gate, return deterministic no-memory.
        if mode in {"RECALL", "RECALL_LLM_RERANK"} and not budgeted:
            logger.info("recall_no_memory_short_circuit", extra={"mode": mode})
            return await self._return_no_memory_response(
                request=request,
                mode=mode,
                external_knowledge_used=False,
                start_time=start_time,
            )

        # 3. Mode instruction + policy
        mode_instruction = self._mode_ctrl.get_instruction(mode)
        policy = self._mode_ctrl.get_policy(mode)

        # 4. Epistemic boundary — mode-based rule:
        #    EXPAND is the ONLY mode that allows external knowledge.
        #    All other modes: external_knowledge_used = False.
        #    Clean. No conditional threshold. Mode = permission.
        external_knowledge_used = policy.can_use_external_knowledge

        # Strict RECALL behavior: deterministic memory output, no LLM generation.
        if mode == "RECALL":
            logger.info(
                "recall_deterministic_response",
                extra={"mode": mode, "memory_count": len(budgeted)},
            )
            return await self._return_recall_response(
                request=request,
                mode=mode,
                memories=budgeted,
                external_knowledge_used=external_knowledge_used,
                start_time=start_time,
            )

        # LLM-assisted recall: LLM selects best memory IDs only; final output stays deterministic.
        if mode == "RECALL_LLM_RERANK":
            logger.info(
                "recall_llm_rerank_response",
                extra={"mode": mode, "memory_count": len(budgeted)},
            )
            return await self._return_recall_llm_rerank_response(
                request=request,
                mode=mode,
                memories=budgeted,
                external_knowledge_used=external_knowledge_used,
                start_time=start_time,
            )

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

        # 7. Validate citations — enforce must_cite_memory_id policy
        self._validate_citations(
            response_text=llm_response.content,
            policy=policy,
            mode=mode,
            memory_count=len(budgeted),
        )

        latency_ms = int((time.monotonic() - start_time) * 1000)
        memory_ids = [uuid.UUID(m.id) for m in budgeted]

        # 8. Log to reasoning_logs
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

    @staticmethod
    def _build_recall_fallback(memories: list[BudgetedMemory]) -> str:
        """Build deterministic RECALL response with explicit [Memory N] citations."""
        lines = ["## 📚 Các memory liên quan\n"]

        for idx, memory in enumerate(memories, start=1):
            lines.append(f"### 🧠 Memory {idx}")
            lines.append(f"> {memory.raw_text.strip()}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _build_recall_rerank_prompt(
        query: str,
        memories: list[BudgetedMemory],
        max_select: int,
    ) -> str:
        """
        Build a strict rerank prompt where LLM is only allowed to return memory indices.

        Output contract:
          {"selected_memory_indices":[1,3,5]}
        """
        candidate_lines: list[str] = []
        for idx, memory in enumerate(memories, start=1):
            candidate_lines.append(f"[Memory {idx}] {memory.raw_text.strip()}")

        candidate_block = "\n".join(candidate_lines)
        return (
            "You are a strict memory reranker.\n"
            "Task: choose the most relevant memories for USER_QUERY from CANDIDATE_MEMORIES.\n"
            "Rules:\n"
            "- Use ONLY candidate memories.\n"
            "- Prioritize direct relevance, not broad same-domain noise.\n"
            f"- Select at most {max_select} memory indices.\n"
            "- If none are relevant, return an empty list.\n"
            "- Return JSON ONLY. No explanation.\n"
            "JSON format: {\"selected_memory_indices\": [1,2,3]}\n\n"
            f"USER_QUERY:\n{query.strip()}\n\n"
            f"CANDIDATE_MEMORIES:\n{candidate_block}\n"
        )

    @staticmethod
    def _parse_rerank_indices(
        llm_text: str,
        memory_count: int,
        max_select: int,
    ) -> tuple[list[int], bool]:
        """
        Parse rerank JSON output from LLM.

        Returns:
          (indices, parsed_ok)
        """
        if not llm_text:
            return [], False

        matched_json = _RERANK_JSON_PATTERN.search(llm_text)
        payload_text = matched_json.group(0) if matched_json else llm_text.strip()

        try:
            parsed = json.loads(payload_text)
        except json.JSONDecodeError:
            return [], False

        raw_indices: list[int] = []

        def _coerce_int(value: object) -> int | None:
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
            return None

        if isinstance(parsed, dict):
            raw = parsed.get("selected_memory_indices", [])
            if isinstance(raw, list):
                raw_indices = [v for x in raw if (v := _coerce_int(x)) is not None]
            else:
                return [], False
        elif isinstance(parsed, list):
            raw_indices = [v for x in parsed if (v := _coerce_int(x)) is not None]
        else:
            return [], False

        valid: list[int] = []
        seen: set[int] = set()
        for idx in raw_indices:
            if idx < 1 or idx > memory_count or idx in seen:
                continue
            valid.append(idx)
            seen.add(idx)
            if len(valid) >= max_select:
                break

        return valid, True

    @staticmethod
    def _pick_memories_by_indices(
        memories: list[BudgetedMemory],
        indices: list[int],
    ) -> list[BudgetedMemory]:
        """Map 1-based indices to memory records in order."""
        selected: list[BudgetedMemory] = []
        for idx in indices:
            selected.append(memories[idx - 1])
        return selected

    async def _return_recall_llm_rerank_response(
        self,
        request: QueryRequest,
        mode: str,
        memories: list[BudgetedMemory],
        external_knowledge_used: bool,
        start_time: float,
    ) -> QueryResponse:
        """
        Use LLM only to rerank/select relevant memory indices,
        then return deterministic memory output.
        """
        max_select = min(5, len(memories))
        rerank_prompt = self._build_recall_rerank_prompt(
            query=request.query,
            memories=memories,
            max_select=max_select,
        )
        llm_response = await self._llm.generate(
            rerank_prompt,
            LLMConfig(temperature=0.0, max_tokens=180),
        )

        selected_indices, parsed_ok = self._parse_rerank_indices(
            llm_text=llm_response.content,
            memory_count=len(memories),
            max_select=max_select,
        )

        if parsed_ok:
            selected_memories = self._pick_memories_by_indices(memories, selected_indices)
            parse_fallback_used = False
        else:
            # Fallback to retrieval ranking when LLM output is malformed.
            selected_memories = memories[:max_select]
            parse_fallback_used = True

        if selected_memories:
            response_text = self._build_recall_fallback(selected_memories)
            memory_ids = [uuid.UUID(m.id) for m in selected_memories]
        else:
            response_text = "Không có memory liên quan tới câu này."
            memory_ids = []

        latency_ms = int((time.monotonic() - start_time) * 1000)
        prompt_hash = hashlib.sha256(rerank_prompt.encode()).hexdigest()

        log = ReasoningLog(
            user_query=request.query,
            mode=mode,
            memory_ids=memory_ids,
            prompt_hash=prompt_hash,
            debug_prompt=None,
            external_knowledge_used=external_knowledge_used,
            confidence_score=0.5,
            response=response_text,
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
            "recall_llm_rerank_complete",
            extra={
                "mode": mode,
                "candidate_count": len(memories),
                "selected_count": len(memory_ids),
                "selected_indices": selected_indices,
                "rerank_parse_fallback": parse_fallback_used,
                "latency_ms": latency_ms,
                "tokens": llm_response.total_tokens,
            },
        )

        return QueryResponse(
            response=response_text,
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

    async def _return_recall_response(
        self,
        request: QueryRequest,
        mode: str,
        memories: list[BudgetedMemory],
        external_knowledge_used: bool,
        start_time: float,
    ) -> QueryResponse:
        """Persist and return deterministic RECALL response."""
        response_text = self._build_recall_fallback(memories)
        latency_ms = int((time.monotonic() - start_time) * 1000)
        memory_ids = [uuid.UUID(m.id) for m in memories]

        log = ReasoningLog(
            user_query=request.query,
            mode=mode,
            memory_ids=memory_ids,
            prompt_hash=None,
            debug_prompt=None,
            external_knowledge_used=external_knowledge_used,
            confidence_score=0.5,
            response=response_text,
            token_usage={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total": 0,
            },
            latency_ms=latency_ms,
        )
        self._session.add(log)
        await self._session.commit()

        return QueryResponse(
            response=response_text,
            mode=mode,
            memory_used=memory_ids,
            token_usage={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total": 0,
            },
            external_knowledge_used=external_knowledge_used,
            latency_ms=latency_ms,
        )

    async def _return_no_memory_response(
        self,
        request: QueryRequest,
        mode: str,
        external_knowledge_used: bool,
        start_time: float,
    ) -> QueryResponse:
        """Persist and return deterministic no-memory response for recall modes."""
        response_text = "Không có memory liên quan đến câu hỏi này."
        latency_ms = int((time.monotonic() - start_time) * 1000)
        memory_ids: list[uuid.UUID] = []

        log = ReasoningLog(
            user_query=request.query,
            mode=mode,
            memory_ids=memory_ids,
            prompt_hash=None,
            debug_prompt=None,
            external_knowledge_used=external_knowledge_used,
            confidence_score=0.5,
            response=response_text,
            token_usage={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total": 0,
            },
            latency_ms=latency_ms,
        )
        self._session.add(log)
        await self._session.commit()

        return QueryResponse(
            response=response_text,
            mode=mode,
            memory_used=memory_ids,
            token_usage={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total": 0,
            },
            external_knowledge_used=external_knowledge_used,
            latency_ms=latency_ms,
        )

    # ─── Citation Validation ──────────────────────────────────────────────────

    def _validate_citations(
        self,
        response_text: str,
        policy: ModePolicy,
        mode: str,
        memory_count: int,
    ) -> None:
        """
        Validate citations in LLM response against policy.

        Checks:
        1. If must_cite_memory_id=True and memories exist → response MUST contain [Memory N]
        2. Any cited [Memory N] index must be within range [1, memory_count]
        3. Out-of-range citations → warning log (fabricated reference)
        """
        cited_indices = set(int(m) for m in _CITATION_PATTERN.findall(response_text))

        # Check 1: policy requires citations but LLM gave none
        if policy.must_cite_memory_id and memory_count > 0 and not cited_indices:
            logger.warning(
                "citation_policy_violation",
                extra={
                    "mode": mode,
                    "memory_count": memory_count,
                    "violation": "must_cite_memory_id=True but no citations found",
                },
            )
            raise PolicyViolationError(
                mode=mode,
                violation="Response must cite memory references but none were found.",
            )

        # Check 2: fabricated citations (index out of range)
        valid_range = set(range(1, memory_count + 1))
        fabricated = cited_indices - valid_range
        if fabricated:
            logger.warning(
                "fabricated_citation_detected",
                extra={
                    "mode": mode,
                    "fabricated_indices": sorted(fabricated),
                    "valid_range": f"1-{memory_count}",
                },
            )
            # Warning only — don't block response, but log for audit
