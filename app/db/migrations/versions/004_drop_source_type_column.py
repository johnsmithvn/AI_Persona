"""
Drop source_type column — move to metadata.source.

Memory Contract V1 puts source info in metadata.source (JSONB)
instead of a top-level column. This simplifies the schema and
follows the contract design principle: extend via metadata, not columns.
"""

from alembic import op

revision: str = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Migrate existing source_type values into metadata.source
    op.execute("""
        UPDATE memory_records
        SET metadata = jsonb_set(
            COALESCE(metadata, '{}'),
            '{source}',
            to_jsonb(source_type)
        )
        WHERE source_type IS NOT NULL
          AND NOT (metadata ? 'source')
    """)

    # 2. Drop the column
    op.execute("ALTER TABLE memory_records DROP COLUMN source_type")


def downgrade() -> None:
    # Re-add column
    op.execute("ALTER TABLE memory_records ADD COLUMN source_type VARCHAR(30) NOT NULL DEFAULT 'manual'")

    # Restore from metadata.source
    op.execute("""
        UPDATE memory_records
        SET source_type = metadata->>'source'
        WHERE metadata ? 'source'
    """)
