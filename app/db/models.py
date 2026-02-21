"""
ORM models — SQLAlchemy 2.0 mapped_column style.
Mapping is 1:1 with DB tables defined in DATA_DESIGN.md.

IMMUTABILITY CONTRACT:
- MemoryRecord.raw_text is NEVER updated after insert.
- Only embedding, embedding_model, importance_score, metadata, and flags may change.
"""

import os
import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    UUID,
    Boolean,
    CheckConstraint,
    Float,
    Index,
    Integer,
    String,
    TIMESTAMP,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Read dimension from env directly to avoid circular import with config
_EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "768"))


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# memory_records — Core table, center of the entire system
# ─────────────────────────────────────────────────────────────────────────────

class MemoryRecord(Base):
    __tablename__ = "memory_records"
    __table_args__ = (
        CheckConstraint(
            "importance_score >= 0 AND importance_score <= 1",
            name="chk_importance_score_range",
        ),
        Index("idx_memory_created_at", "created_at"),
        Index("idx_memory_content_type", "content_type"),
        Index("idx_memory_embedding_model", "embedding_model"),
        # HNSW + GIN + UNIQUE indexes created in Alembic migration (raw SQL)
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Immutable content
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(30), nullable=False, default="note")

    # Embedding — may be NULL until worker processes the job
    embedding: Mapped[Optional[list]] = mapped_column(Vector(_EMBEDDING_DIMENSION), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Integrity
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Scoring
    importance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Flexible metadata (JSONB)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    # Selective forgetting flags
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exclude_from_retrieval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<MemoryRecord id={self.id} type={self.content_type}>"


# ─────────────────────────────────────────────────────────────────────────────
# embedding_jobs — Async embedding pipeline queue
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingJob(Base):
    __tablename__ = "embedding_jobs"
    __table_args__ = (
        Index("idx_embedding_jobs_status", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    # status: 'pending' | 'processing' | 'completed' | 'failed'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<EmbeddingJob id={self.id} status={self.status}>"


# ─────────────────────────────────────────────────────────────────────────────
# reasoning_logs — Audit trail for all reasoning sessions
# ─────────────────────────────────────────────────────────────────────────────

class ReasoningLog(Base):
    __tablename__ = "reasoning_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(30), nullable=False)

    # Array of memory UUIDs used in this reasoning session
    memory_ids: Mapped[list] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )

    # Audit fields
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    debug_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_knowledge_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.5)

    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ReasoningLog id={self.id} mode={self.mode}>"
