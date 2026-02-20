"""
MemoryService — Business logic for saving memory.

Contract:
- Computes SHA256 checksum before insert.
- Detects duplicates via checksum.
- NEVER calls LLM or embedding API directly.
- Creates embedding_job after insert.
"""

import hashlib
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MemoryRecord
from app.exceptions.handlers import DuplicateMemoryError, MemoryNotFoundError
from app.logging.logger import logger
from app.memory.repository import MemoryRepository
from app.schemas.memory import MemoryCreateRequest, MemoryResponse


def _compute_checksum(text: str) -> str:
    """SHA256 hex digest of the raw text — used for deduplication and integrity."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _to_response(record: MemoryRecord) -> MemoryResponse:
    return MemoryResponse(
        id=record.id,
        raw_text=record.raw_text,
        content_type=record.content_type,
        source_type=record.source_type,
        checksum=record.checksum,
        importance_score=record.importance_score,
        metadata=record.metadata_ or {},
        is_archived=record.is_archived,
        exclude_from_retrieval=record.exclude_from_retrieval,
        is_summary=record.is_summary,
        has_embedding=record.embedding is not None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class MemoryService:
    """Business logic for memory creation and retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = MemoryRepository(session)
        self._session = session

    async def save_memory(self, request: MemoryCreateRequest) -> MemoryResponse:
        """
        Save a memory:
        1. Compute SHA256 checksum
        2. Check for duplicate
        3. Insert raw_text → DB
        4. Create embedding_job (pending)
        5. Commit transaction
        6. Return MemoryResponse
        """
        checksum = _compute_checksum(request.raw_text)

        # Duplicate check
        existing = await self._repo.get_by_checksum(checksum)
        if existing:
            logger.warning("duplicate_memory_attempt", extra={"checksum": checksum})
            raise DuplicateMemoryError(checksum)

        record = MemoryRecord(
            raw_text=request.raw_text,
            content_type=request.content_type,
            source_type=request.source_type,
            checksum=checksum,
            importance_score=request.importance_score,
            metadata_=request.metadata,
        )

        record = await self._repo.insert(record)
        await self._repo.create_embedding_job(record.id)
        await self._session.commit()

        logger.info("memory_saved", extra={"memory_id": str(record.id), "content_type": record.content_type})
        return _to_response(record)

    async def get_memory(self, memory_id: uuid.UUID) -> MemoryResponse:
        """Retrieve a single memory by ID."""
        record = await self._repo.get_by_id(memory_id)
        return _to_response(record)

    async def archive_memory(
        self,
        memory_id: uuid.UUID,
        is_archived: bool = True,
        exclude_from_retrieval: bool = False,
    ) -> MemoryResponse:
        """Soft-archive a memory (selective forgetting — never deletes raw_text)."""
        await self._repo.get_by_id(memory_id)  # validate exists
        await self._repo.update_flags(memory_id, is_archived=is_archived, exclude_from_retrieval=exclude_from_retrieval)
        await self._session.commit()
        record = await self._repo.get_by_id(memory_id)
        return _to_response(record)
