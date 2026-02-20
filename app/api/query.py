"""
Query (Reasoning) API endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_embedding_adapter, get_llm_adapter
from app.llm.adapter import LLMAdapter
from app.llm.embedding_adapter import EmbeddingAdapter
from app.reasoning.service import ReasoningService
from app.schemas.query import QueryRequest, QueryResponse

router = APIRouter(prefix="/api/v1/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    llm_adapter: LLMAdapter = Depends(get_llm_adapter),
    embedding_adapter: EmbeddingAdapter = Depends(get_embedding_adapter),
) -> QueryResponse:
    """
    Core reasoning endpoint.
    Retrieves relevant memories → applies mode → builds prompt → calls LLM.
    """
    service = ReasoningService(db, llm_adapter, embedding_adapter)
    return await service.process_query(request)
