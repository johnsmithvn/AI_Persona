"""
Initial database schema migration.

Creates:
  - ENUM types (content_type, source_type)
  - memory_records table with all columns from DATA_DESIGN.md
  - embedding_jobs table
  - reasoning_logs table
  - All indexes (HNSW, B-Tree, GIN, UNIQUE)
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── Extensions ──────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # ─── ENUM types ───────────────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE content_type AS ENUM (
                'note', 'conversation', 'quote', 'repo',
                'article', 'pdf', 'transcript', 'idea', 'reflection', 'log'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE source_type AS ENUM (
                'manual', 'api', 'import', 'ocr', 'whisper', 'crawler'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$
    """)

    # ─── memory_records ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE memory_records (
            id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            raw_text                TEXT NOT NULL,
            content_type            content_type NOT NULL DEFAULT 'note',
            source_type             source_type NOT NULL DEFAULT 'manual',

            embedding               vector(1536),
            embedding_model         VARCHAR(100),

            checksum                VARCHAR(64) NOT NULL,
            version                 INTEGER NOT NULL DEFAULT 1,

            importance_score        FLOAT CHECK (importance_score >= 0 AND importance_score <= 1),
            metadata                JSONB NOT NULL DEFAULT '{}',

            is_archived             BOOLEAN NOT NULL DEFAULT false,
            exclude_from_retrieval  BOOLEAN NOT NULL DEFAULT false,
            is_summary              BOOLEAN NOT NULL DEFAULT false,

            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ─── embedding_jobs ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE embedding_jobs (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            memory_id       UUID NOT NULL REFERENCES memory_records(id) ON DELETE CASCADE,
            status          VARCHAR(20) NOT NULL DEFAULT 'pending',
            attempts        INTEGER DEFAULT 0,
            max_attempts    INTEGER DEFAULT 3,
            error_message   TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at    TIMESTAMPTZ
        )
    """)

    # ─── reasoning_logs ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE reasoning_logs (
            id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_query               TEXT NOT NULL,
            mode                     VARCHAR(30) NOT NULL,
            memory_ids               UUID[] DEFAULT '{}',
            prompt_hash              VARCHAR(64),
            debug_prompt             TEXT,
            external_knowledge_used  BOOLEAN DEFAULT false,
            confidence_score         FLOAT DEFAULT 0.5,
            response                 TEXT,
            token_usage              JSONB DEFAULT '{}',
            latency_ms               INTEGER,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ─── Indexes ──────────────────────────────────────────────────────────

    # 1. HNSW index for semantic search (most critical)
    op.execute("""
        CREATE INDEX idx_memory_embedding
        ON memory_records
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200)
    """)

    # 2. B-Tree: time filter
    op.execute("""
        CREATE INDEX idx_memory_created_at
        ON memory_records (created_at DESC)
    """)

    # 3. B-Tree: content_type filter
    op.execute("""
        CREATE INDEX idx_memory_content_type
        ON memory_records (content_type)
    """)

    # 4. GIN: JSONB metadata filter
    op.execute("""
        CREATE INDEX idx_memory_metadata
        ON memory_records USING GIN (metadata)
    """)

    # 5. UNIQUE: duplicate prevention via checksum
    op.execute("""
        CREATE UNIQUE INDEX idx_memory_checksum
        ON memory_records (checksum)
    """)

    # 6. Embedding jobs — worker poll
    op.execute("""
        CREATE INDEX idx_embedding_jobs_status
        ON embedding_jobs (status, created_at ASC)
    """)

    # 7. Embedding model isolation
    op.execute("""
        CREATE INDEX idx_memory_embedding_model
        ON memory_records (embedding_model)
    """)

    # ─── Auto-update updated_at trigger ───────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE TRIGGER trg_memory_updated_at
        BEFORE UPDATE ON memory_records
        FOR EACH ROW EXECUTE FUNCTION update_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_memory_updated_at ON memory_records")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at")
    op.execute("DROP TABLE IF EXISTS reasoning_logs")
    op.execute("DROP TABLE IF EXISTS embedding_jobs")
    op.execute("DROP TABLE IF EXISTS memory_records")
    op.execute("DROP TYPE IF EXISTS content_type")
    op.execute("DROP TYPE IF EXISTS source_type")
