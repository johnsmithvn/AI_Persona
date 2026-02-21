"""
Change embedding vector dimension from 1536 to configurable value.

This migration:
1. Drops the HNSW index (required before altering vector column)
2. Alters embedding column type from vector(1536) to vector(768)
3. Recreates the HNSW index with new dimension

NOTE: This will invalidate any existing embeddings with dimension != 768.
      Re-embed existing records after running this migration.
"""

from alembic import op

revision: str = "002"
down_revision = "001"
branch_labels = None
depends_on = None

# Change these values if you need a different dimension
NEW_DIMENSION = 768
OLD_DIMENSION = 1536


def upgrade() -> None:
    # 1. Drop HNSW index (can't alter column type with index present)
    op.execute("DROP INDEX IF EXISTS idx_memory_embedding")

    # 2. Clear existing embeddings (incompatible dimension)
    op.execute("UPDATE memory_records SET embedding = NULL WHERE embedding IS NOT NULL")

    # 3. Alter vector column dimension
    op.execute(f"ALTER TABLE memory_records ALTER COLUMN embedding TYPE vector({NEW_DIMENSION})")

    # 4. Recreate HNSW index with new dimension
    op.execute(f"""
        CREATE INDEX idx_memory_embedding
        ON memory_records
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_memory_embedding")
    op.execute("UPDATE memory_records SET embedding = NULL WHERE embedding IS NOT NULL")
    op.execute(f"ALTER TABLE memory_records ALTER COLUMN embedding TYPE vector({OLD_DIMENSION})")
    op.execute(f"""
        CREATE INDEX idx_memory_embedding
        ON memory_records
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200)
    """)
