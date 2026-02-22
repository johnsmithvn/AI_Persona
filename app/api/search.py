"""
Search API endpoint — semantic search with ranking.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_embedding_adapter
from app.llm.embedding_adapter import EmbeddingAdapter
from app.retrieval.ranking import get_ranking_profile
from app.retrieval.search import RetrievalService, SearchFilters
from app.schemas.search import MemorySearchResult, SearchRequest, SearchResponse

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_memories(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    embedding_adapter: EmbeddingAdapter = Depends(get_embedding_adapter),
) -> SearchResponse:
    """
    Semantic search over memory records.
    Uses neutral ranking profile for final_score:
    semantic + recency + importance with default app weights (0.60/0.15/0.25).
    """
    retrieval = RetrievalService(db, embedding_adapter)
    filters = SearchFilters(
        content_type=request.content_type,
        start_date=request.start_date,
        end_date=request.end_date,
        threshold=request.threshold,
        limit=request.limit,
        metadata_filter=request.metadata_filter,
        include_summaries=request.include_summaries,
    )
    memories = await retrieval.search(request.query, filters)
    ranking_profile = get_ranking_profile(filters.mode)

    results = [
        MemorySearchResult(
            id=m.id,  # type: ignore[arg-type]
            raw_text=m.raw_text,
            content_type=m.content_type,
            importance_score=m.importance_score,
            created_at=m.created_at,
            metadata={},
            similarity=m.similarity,
            final_score=m.final_score,
            is_summary=m.is_summary,
        )
        for m in memories
    ]

    return SearchResponse(
        results=results,
        total=len(results),
        query=request.query,
        ranking_profile=ranking_profile,
    )
