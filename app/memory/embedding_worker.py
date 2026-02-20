"""
EmbeddingWorker — Background processor for pending embedding jobs.

Lifecycle per job:
  pending → processing → completed
                       ↘ failed (if attempts >= max_attempts)
                       ↘ pending (retry if attempts < max_attempts)

NEVER blocks the API. Runs in a separate process.
"""

import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.llm.embedding_adapter import EmbeddingAdapter
from app.logging.logger import logger
from app.memory.repository import MemoryRepository

settings = get_settings()


class EmbeddingWorker:
    """Processes pending embedding jobs from the DB."""

    def __init__(self, session: AsyncSession, embedding_adapter: EmbeddingAdapter) -> None:
        self._session = session
        self._adapter = embedding_adapter
        self._repo = MemoryRepository(session)

    async def process_pending_jobs(self) -> int:
        """
        Process a batch of pending jobs.
        Returns the number of jobs successfully processed.
        """
        jobs = await self._repo.get_pending_jobs(batch_size=settings.embedding_worker_batch_size)
        if not jobs:
            return 0

        processed = 0
        for job in jobs:
            try:
                # 1. Mark as processing (prevent double-processing by parallel workers)
                await self._repo.mark_job_processing(job.id)
                await self._session.commit()

                # 2. Load the memory record
                memory = await self._repo.get_by_id(job.memory_id)

                # 3. Generate embedding via adapter (never direct OpenAI call)
                embedding = await self._adapter.embed(memory.raw_text)

                # 4. Persist embedding to memory_records
                await self._repo.update_embedding(
                    memory_id=memory.id,
                    embedding=embedding,
                    model=self._adapter.model_name,
                )

                # 5. Mark job as completed
                await self._repo.mark_job_completed(job.id)
                await self._session.commit()

                logger.info(
                    "embedding_job_completed",
                    extra={"job_id": str(job.id), "memory_id": str(job.memory_id)},
                )
                processed += 1

            except Exception as exc:
                await self._session.rollback()
                new_attempts = (job.attempts or 0) + 1
                await self._repo.mark_job_failed(
                    job_id=job.id,
                    error=str(exc),
                    attempts=new_attempts,
                )
                await self._session.commit()
                logger.error(
                    "embedding_job_failed",
                    extra={
                        "job_id": str(job.id),
                        "memory_id": str(job.memory_id),
                        "attempts": new_attempts,
                        "error": str(exc),
                    },
                )

        return processed
