"""
Background embedding worker entrypoint.

Usage:
    python -m workers.run_embedding

Runs continuously, polling for pending embedding jobs at a configurable interval.
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is in path when running as module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.llm.openai_embedding_adapter import OpenAIEmbeddingAdapter
from app.logging.logger import logger
from app.memory.embedding_worker import EmbeddingWorker

settings = get_settings()


async def run_loop() -> None:
    """Main worker loop — polls for pending jobs indefinitely."""
    adapter = OpenAIEmbeddingAdapter()
    logger.info("embedding_worker_started", extra={
        "model": adapter.model_name,
        "interval_seconds": settings.embedding_worker_interval_seconds,
        "batch_size": settings.embedding_worker_batch_size,
    })

    while True:
        try:
            async with AsyncSessionLocal() as session:
                worker = EmbeddingWorker(session, adapter)
                processed = await worker.process_pending_jobs()
                if processed > 0:
                    logger.info("batch_processed", extra={"count": processed})
        except Exception as exc:
            logger.error("worker_loop_error", extra={"error": str(exc)})

        await asyncio.sleep(settings.embedding_worker_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_loop())
