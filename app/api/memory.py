"""
Memory API endpoints — HTTP layer only, no business logic.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_embedding_adapter
from app.llm.embedding_adapter import EmbeddingAdapter
from app.memory.service import MemoryService
from app.schemas.memory import MemoryArchiveRequest, MemoryCreateRequest, MemoryResponse

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    request: MemoryCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> MemoryResponse:
    """Save a new memory. Embedding is created asynchronously by the worker."""
    service = MemoryService(db)
    return await service.save_memory(request)


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MemoryResponse:
    """Retrieve a single memory by ID."""
    service = MemoryService(db)
    return await service.get_memory(memory_id)


@router.patch("/{memory_id}/archive", response_model=MemoryResponse)
async def archive_memory(
    memory_id: uuid.UUID,
    request: MemoryArchiveRequest,
    db: AsyncSession = Depends(get_db),
) -> MemoryResponse:
    """
    Soft-archive a memory (selective forgetting).
    raw_text is NEVER deleted.
    """
    service = MemoryService(db)
    return await service.archive_memory(
        memory_id=memory_id,
        is_archived=request.is_archived,
        exclude_from_retrieval=request.exclude_from_retrieval,
    )
