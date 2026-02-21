"""
MemoryRepository — Database access layer for memory_records and embedding_jobs.
Pure CRUD. No business logic. No LLM calls.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmbeddingJob, MemoryRecord
from app.exceptions.handlers import DuplicateMemoryError, MemoryNotFoundError


class MemoryRepository:
    """Data access layer for memory_records and embedding_jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ─── memory_records ───────────────────────────────────────────────────

    async def insert(self, record: MemoryRecord) -> MemoryRecord:
        """Insert a new memory record. Raises DuplicateMemoryError on checksum collision."""
        try:
            self._session.add(record)
            await self._session.flush()
            await self._session.refresh(record)
            return record
        except IntegrityError as exc:
            await self._session.rollback()
            if "idx_memory_checksum" in str(exc.orig) or "unique" in str(exc.orig).lower():
                raise DuplicateMemoryError(record.checksum) from exc
            raise

    async def get_by_id(self, memory_id: uuid.UUID) -> MemoryRecord:
        """Fetch a single MemoryRecord by ID. Raises MemoryNotFoundError if missing."""
        result = await self._session.execute(
            select(MemoryRecord).where(MemoryRecord.id == memory_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise MemoryNotFoundError(str(memory_id))
        return record

    async def get_by_checksum(self, checksum: str) -> Optional[MemoryRecord]:
        """Return existing record for the given checksum, or None."""
        result = await self._session.execute(
            select(MemoryRecord).where(MemoryRecord.checksum == checksum)
        )
        return result.scalar_one_or_none()

    async def update_embedding(
        self,
        memory_id: uuid.UUID,
        embedding: list[float],
        model: str,
    ) -> None:
        """Update the embedding vector and model name for a record."""
        await self._session.execute(
            update(MemoryRecord)
            .where(MemoryRecord.id == memory_id)
            .values(embedding=embedding, embedding_model=model)
        )

    async def update_flags(
        self,
        memory_id: uuid.UUID,
        is_archived: Optional[bool] = None,
        exclude_from_retrieval: Optional[bool] = None,
    ) -> None:
        """Update soft-delete / exclusion flags."""
        values: dict = {}
        if is_archived is not None:
            values["is_archived"] = is_archived
        if exclude_from_retrieval is not None:
            values["exclude_from_retrieval"] = exclude_from_retrieval
        if values:
            await self._session.execute(
                update(MemoryRecord).where(MemoryRecord.id == memory_id).values(**values)
            )

    async def get_distinct_person_names(self) -> list[str]:
        """
        Return distinct person names from memory records that have the 'person' tag.
        Used by CLI for person_name suggestion flow.
        """
        from sqlalchemy import text

        result = await self._session.execute(
            text(
                """
                SELECT DISTINCT metadata->'extra'->>'person_name' AS name
                FROM memory_records
                WHERE metadata->'tags' ? 'person'
                    AND metadata->'extra' IS NOT NULL
                    AND metadata->'extra'->>'person_name' IS NOT NULL
                    AND metadata->'extra'->>'person_name' <> ''
                ORDER BY name
                """
            )
        )
        return [row[0] for row in result.fetchall()]

    # ─── embedding_jobs ───────────────────────────────────────────────────

    async def create_embedding_job(self, memory_id: uuid.UUID) -> EmbeddingJob:
        """Create a pending embedding job for a given memory."""
        job = EmbeddingJob(memory_id=memory_id, status="pending")
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def get_pending_jobs(self, batch_size: int = 10) -> list[EmbeddingJob]:
        """Fetch a batch of pending embedding jobs ordered by creation time.

        Uses SELECT FOR UPDATE SKIP LOCKED so that two concurrent worker processes
        cannot claim the same job. Each worker atomically locks the rows it fetches.
        """
        result = await self._session.execute(
            select(EmbeddingJob)
            .where(EmbeddingJob.status == "pending")
            .order_by(EmbeddingJob.created_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def mark_job_processing(self, job_id: uuid.UUID) -> None:
        await self._session.execute(
            update(EmbeddingJob)
            .where(EmbeddingJob.id == job_id)
            .values(status="processing")
        )

    async def mark_job_completed(self, job_id: uuid.UUID) -> None:
        await self._session.execute(
            update(EmbeddingJob)
            .where(EmbeddingJob.id == job_id)
            .values(status="completed", completed_at=datetime.utcnow())
        )

    async def mark_job_failed(self, job_id: uuid.UUID, error: str, attempts: int) -> None:
        new_status = "failed" if attempts >= 3 else "pending"
        await self._session.execute(
            update(EmbeddingJob)
            .where(EmbeddingJob.id == job_id)
            .values(status=new_status, error_message=error, attempts=attempts)
        )
