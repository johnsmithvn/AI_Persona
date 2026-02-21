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
from app.retrieval.ranking import compute_final_score, deduplicate_memories

settings = get_settings()


@dataclass
class SearchFilters:
    content_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    threshold: float = 0.7
    limit: int = 30
    metadata_filter: Optional[dict[str, Any]] = None
    include_summaries: bool = False
    mode: str = "RECALL"


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
              AND embedding_model = :embedding_model
              AND (:content_type IS NULL OR CAST(:content_type AS text) = '' OR content_type = CAST(:content_type AS content_type))
              AND (:start_date IS NULL OR created_at >= :start_date)
              AND (:end_date IS NULL OR created_at <= :end_date)
              AND (embedding <=> CAST(:embedding AS vector)) < :threshold
              AND (:include_summaries = true OR is_summary = false)
              AND (:metadata_filter IS NULL OR metadata @> CAST(:metadata_filter AS jsonb))
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT 500
        )
        SELECT *
        FROM candidates
        ORDER BY similarity DESC
    """)

    def __init__(self, session: AsyncSession, embedding_adapter: EmbeddingAdapter) -> None:
        self._session = session
        self._adapter = embedding_adapter

    async def search(
        self,
        query: str,
        filters: SearchFilters,
    ) -> list[BudgetedMemory]:
        """
        Full semantic search pipeline:
        1. Embed query (via EmbeddingAdapter — never direct OpenAI call)
        2. Execute SQL with cosine + filters + embedding_model isolation
        3. Apply ranking formula (mode-aware)
        4. Deduplicate
        5. Return ranked list (no token budget — that's TokenGuard's job)
        """
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
                    "content_type": filters.content_type or "",
                    "start_date": filters.start_date,
                    "end_date": filters.end_date,
                    "threshold": filters.threshold,
                    "include_summaries": filters.include_summaries,
                    "metadata_filter": json.dumps(filters.metadata_filter) if filters.metadata_filter else None,
                },
            )
            rows = result.fetchall()

        except Exception as exc:
            logger.error("retrieval_failed", extra={"error": str(exc)})
            raise RetrievalError(str(exc)) from exc

        if not rows:
            return []

        # Step 3: Apply ranking formula
        ranked: list[BudgetedMemory] = []
        for row in rows:
            final_score = compute_final_score(
                similarity=float(row.similarity),
                created_at=row.created_at,
                importance=row.importance_score,
                mode=filters.mode,
            )
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

        # Step 5: Return top N
        logger.info(
            "retrieval_complete",
            extra={"total_candidates": len(rows), "after_dedup": len(ranked), "mode": filters.mode},
        )
        return ranked[: filters.limit]
