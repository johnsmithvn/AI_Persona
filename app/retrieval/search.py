"""
RetrievalService — Semantic search engine.

Responsibilities:
- Embed user query via EmbeddingAdapter
- Execute SQL with cosine distance + all filters
- Apply ranking formula
- Return ranked, deduplicated memories within token budget

NEVER calls LLM. NEVER reasons. Only finds.
Must filter by embedding_model to prevent cross-model embedding comparison.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.token_guard import BudgetedMemory
from app.exceptions.handlers import RetrievalError
from app.llm.embedding_adapter import EmbeddingAdapter
from app.logging.logger import logger
from app.retrieval.ranking import (
    compute_exposure_diversity_bonus,
    compute_final_score,
    compute_query_lexical_bonus,
    deduplicate_memories,
    get_ranking_profile,
)

settings = get_settings()

_MODE_SEMANTIC_MIN: dict[str, float] = {
    "RECALL": 0.65,
    "RECALL_LLM_RERANK": 0.60,
    "SYNTHESIZE": 0.60,
    "REFLECT": 0.55,
    "CHALLENGE": 0.60,
    "EXPAND": 0.52,
}

_MODE_RESULT_LIMITS: dict[str, int] = {
    "RECALL": 5,
    "RECALL_LLM_RERANK": 12,
    "SYNTHESIZE": 8,
    "REFLECT": 8,
    "CHALLENGE": 4,
    "EXPAND": 10,
}

_DIVERSITY_MIN_SIMILARITY = 0.70
_COOLDOWN_MODES = {"RECALL", "RECALL_LLM_RERANK", "CHALLENGE"}


@dataclass
class SearchFilters:
    content_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    threshold: float = 0.45
    limit: int = 30
    metadata_filter: Optional[dict[str, Any]] = None
    include_summaries: bool = False
    # /search uses None -> NEUTRAL ranking profile.
    # /query passes reasoning mode -> mode-aware ranking profile.
    mode: Optional[str] = None


class RetrievalService:
    """
    Semantic retrieval engine.
    Queries DB directly (it is an independent layer, not under Reasoning).
    """

    # Production SQL — executes via pgvector HNSW index
    _SEARCH_SQL = text("""
        WITH candidates AS (
            SELECT
                id,
                raw_text,
                content_type,
                importance_score,
                created_at,
                metadata,
                is_summary,
                1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM memory_records
            WHERE embedding IS NOT NULL
              AND exclude_from_retrieval = false
              AND is_archived = false
              AND embedding_model = CAST(:embedding_model AS VARCHAR)
              AND (
                    CAST(:content_type AS VARCHAR) IS NULL
                    OR content_type = CAST(:content_type AS VARCHAR)
              )
              AND (
                    CAST(:start_date AS TIMESTAMPTZ) IS NULL
                    OR created_at >= CAST(:start_date AS TIMESTAMPTZ)
              )
              AND (
                    CAST(:end_date AS TIMESTAMPTZ) IS NULL
                    OR created_at <= CAST(:end_date AS TIMESTAMPTZ)
              )
              AND (CAST(:include_summaries AS BOOLEAN) = true OR is_summary = false)
              AND (
                    CAST(:metadata_filter AS JSONB) IS NULL
                    OR metadata @> CAST(:metadata_filter AS JSONB)
              )
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT CAST(:candidate_pool AS INTEGER)
        )
        SELECT *
        FROM candidates
        ORDER BY similarity DESC
    """)
    _USAGE_COUNTS_SQL = text("""
        SELECT
            used.memory_id AS memory_id,
            COUNT(*)::INT AS retrieval_count
        FROM reasoning_logs rl
        CROSS JOIN LATERAL UNNEST(rl.memory_ids) AS used(memory_id)
        WHERE used.memory_id = ANY(CAST(:candidate_ids AS UUID[]))
        GROUP BY used.memory_id
    """)
    _RECENT_QUERY_USAGE_SQL = text("""
        WITH recent_logs AS (
            SELECT memory_ids
            FROM reasoning_logs
            WHERE mode = CAST(:mode AS VARCHAR)
              AND lower(trim(user_query)) = CAST(:normalized_query AS VARCHAR)
            ORDER BY created_at DESC
            LIMIT CAST(:log_limit AS INTEGER)
        )
        SELECT DISTINCT used.memory_id AS memory_id
        FROM recent_logs rl
        CROSS JOIN LATERAL UNNEST(rl.memory_ids) AS used(memory_id)
    """)

    def __init__(self, session: AsyncSession, embedding_adapter: EmbeddingAdapter) -> None:
        self._session = session
        self._adapter = embedding_adapter

    async def _load_usage_counts(self, candidate_ids: list[uuid.UUID]) -> dict[str, int]:
        """
        Return past retrieval usage count for candidate memories.

        Data source: reasoning_logs.memory_ids (UUID[]).
        """
        if not candidate_ids:
            return {}

        result = await self._session.execute(
            self._USAGE_COUNTS_SQL,
            {"candidate_ids": candidate_ids},
        )
        rows = result.fetchall()
        return {str(row.memory_id): int(row.retrieval_count) for row in rows}

    async def _load_recent_query_memory_ids(
        self,
        *,
        mode: str,
        normalized_query: str,
        log_limit: int,
    ) -> set[str]:
        """
        Return memory IDs used in recent logs for the same (mode, query).

        Used as a soft cooldown so repeated identical queries are less repetitive
        when equivalent alternatives exist.
        """
        if not mode or not normalized_query or log_limit <= 0:
            return set()

        result = await self._session.execute(
            self._RECENT_QUERY_USAGE_SQL,
            {
                "mode": mode,
                "normalized_query": normalized_query,
                "log_limit": log_limit,
            },
        )
        rows = result.fetchall()
        return {str(row.memory_id) for row in rows}

    @staticmethod
    def _normalize_query_key(query: str) -> str:
        """Normalize query string for repeat-detection key."""
        return " ".join((query or "").strip().lower().split())

    async def search(
        self,
        query: str,
        filters: SearchFilters,
    ) -> list[BudgetedMemory]:
        """
        Full semantic search pipeline:
        1. Embed query (via EmbeddingAdapter — never direct OpenAI call)
        2. Execute SQL with cosine + filters + embedding_model isolation
        3. Apply ranking formula (neutral for /search, mode-aware for /query)
        4. Deduplicate
        5. Return ranked list (no token budget — that's TokenGuard's job)
        """
        mode_key = (filters.mode or "").upper().strip()
        recent_query_ids: set[str] = set()
        cooldown_reordered = False
        try:
            # Step 1: embed query
            query_embedding = await self._adapter.embed(query)
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            # Step 2: execute SQL
            result = await self._session.execute(
                self._SEARCH_SQL,
                {
                    "embedding": embedding_str,
                    "embedding_model": self._adapter.model_name,
                    "content_type": filters.content_type or None,
                    "start_date": filters.start_date,
                    "end_date": filters.end_date,
                    "candidate_pool": settings.retrieval_candidate_pool,
                    "include_summaries": filters.include_summaries,
                    "metadata_filter": json.dumps(filters.metadata_filter) if filters.metadata_filter else None,
                },
            )
            rows = result.fetchall()

            requested_similarity_floor = max(0.0, min(1.0, 1.0 - filters.threshold))
            absolute_floor = settings.retrieval_absolute_similarity_floor
            mode_floor = _MODE_SEMANTIC_MIN.get(mode_key, absolute_floor)
            semantic_floor = max(absolute_floor, mode_floor, requested_similarity_floor)

            raw_candidate_count = len(rows)
            rows = [row for row in rows if float(row.similarity) >= semantic_floor]

            # Apply exposure-aware diversity only for mode-aware requests (/query),
            # and only after semantic floors.
            diversity_applied = bool(filters.mode)
            usage_counts: dict[str, int] = {}
            if diversity_applied and rows:
                usage_counts = await self._load_usage_counts([row.id for row in rows])

            # For repeated same-query calls, gently down-prioritize memories that were
            # just used in recent responses, but only inside already relevant candidates.
            if mode_key in _COOLDOWN_MODES and settings.retrieval_query_cooldown_logs > 0 and rows:
                recent_query_ids = await self._load_recent_query_memory_ids(
                    mode=mode_key,
                    normalized_query=self._normalize_query_key(query),
                    log_limit=settings.retrieval_query_cooldown_logs,
                )

        except Exception as exc:
            logger.error("retrieval_failed", extra={"error": str(exc)})
            raise RetrievalError(str(exc)) from exc

        if not rows:
            logger.info(
                "retrieval_no_match_after_semantic_floors",
                extra={
                    "raw_candidates": raw_candidate_count,
                    "semantic_floor": semantic_floor,
                    "mode_floor": mode_floor,
                    "requested_similarity_floor": requested_similarity_floor,
                    "mode_input": filters.mode,
                },
            )
            return []

        # Step 3: Apply ranking formula
        ranking_profile = get_ranking_profile(filters.mode)
        ranked: list[BudgetedMemory] = []
        lexical_boosted = 0
        for row in rows:
            base_score = compute_final_score(
                similarity=float(row.similarity),
                created_at=row.created_at,
                importance=row.importance_score,
                mode=filters.mode,
            )
            diversity_bonus = 0.0
            if diversity_applied and float(row.similarity) >= _DIVERSITY_MIN_SIMILARITY:
                diversity_bonus = compute_exposure_diversity_bonus(
                    retrieval_count=usage_counts.get(str(row.id), 0),
                )
            lexical_bonus = compute_query_lexical_bonus(
                query=query,
                memory_text=row.raw_text,
                mode=filters.mode,
            )
            if lexical_bonus > 0:
                lexical_boosted += 1
            final_score = base_score + diversity_bonus + lexical_bonus
            ranked.append(
                BudgetedMemory(
                    id=str(row.id),
                    raw_text=row.raw_text,
                    content_type=row.content_type,
                    created_at=row.created_at,
                    importance_score=row.importance_score or 0.5,
                    final_score=final_score,
                    similarity=float(row.similarity),
                    is_summary=row.is_summary,
                )
            )

        # Step 4: Sort + deduplicate
        ranked.sort(key=lambda m: m.final_score, reverse=True)
        ranked = deduplicate_memories(ranked)
        after_dedup = len(ranked)

        # Step 4.1: Keep only score-near cluster around top result.
        top_score = ranked[0].final_score if ranked else 0.0
        gap_threshold = settings.retrieval_score_gap_threshold
        ranked = [
            memory
            for memory in ranked
            if (top_score - memory.final_score) <= gap_threshold
        ]
        after_gap = len(ranked)

        # Step 4.2: Soft cooldown reorder for repeated exact query.
        # Keep precision: reorder only within already-gated candidates.
        if recent_query_ids and ranked:
            fresh = [memory for memory in ranked if memory.id not in recent_query_ids]
            repeated = [memory for memory in ranked if memory.id in recent_query_ids]
            if fresh:
                ranked = fresh + repeated
                cooldown_reordered = True

        # Step 4.3: Mode-specific hard cap (precision > recall).
        mode_limit = _MODE_RESULT_LIMITS.get(mode_key, filters.limit)
        final_limit = min(filters.limit, mode_limit)
        ranked = ranked[:final_limit]

        # Step 5: Return top N
        logger.info(
            "retrieval_complete",
            extra={
                "raw_candidates": raw_candidate_count,
                "after_semantic_floor": len(rows),
                "after_dedup": after_dedup,
                "after_gap": after_gap,
                "returned": len(ranked),
                "ranking_profile": ranking_profile,
                "mode_input": filters.mode,
                "diversity_applied": diversity_applied,
                "max_usage_count": max(usage_counts.values(), default=0) if diversity_applied else 0,
                "lexical_boosted": lexical_boosted,
                "semantic_floor": semantic_floor,
                "mode_limit": mode_limit,
                "score_gap_threshold": gap_threshold,
                "query_cooldown_pool": len(recent_query_ids),
                "cooldown_reordered": cooldown_reordered,
            },
        )
        return ranked
