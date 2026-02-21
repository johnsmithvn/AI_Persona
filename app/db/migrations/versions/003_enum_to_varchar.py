"""
Convert content_type and source_type from PostgreSQL ENUM to VARCHAR.

Reason: SQLAlchemy ORM uses String(30) but initial migration created
PostgreSQL ENUM types. asyncpg strictly enforces type matching and
rejects VARCHAR inserts into ENUM columns.

Additionally, VARCHAR is easier to extend (no ALTER TYPE needed for new values).
Validation is handled at application layer (Pydantic schemas).
"""

from alembic import op

revision: str = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop defaults first (they reference ENUM type and block DROP TYPE)
    op.execute("ALTER TABLE memory_records ALTER COLUMN content_type DROP DEFAULT")
    op.execute("ALTER TABLE memory_records ALTER COLUMN source_type DROP DEFAULT")

    # Convert content_type: ENUM → VARCHAR(30)
    op.execute("""
        ALTER TABLE memory_records
        ALTER COLUMN content_type TYPE VARCHAR(30)
        USING content_type::text
    """)

    # Convert source_type: ENUM → VARCHAR(30)
    op.execute("""
        ALTER TABLE memory_records
        ALTER COLUMN source_type TYPE VARCHAR(30)
        USING source_type::text
    """)

    # Restore defaults as plain strings
    op.execute("ALTER TABLE memory_records ALTER COLUMN content_type SET DEFAULT 'note'")
    op.execute("ALTER TABLE memory_records ALTER COLUMN source_type SET DEFAULT 'manual'")

    # Drop old ENUM types (safe now — no dependencies)
    op.execute("DROP TYPE IF EXISTS content_type")
    op.execute("DROP TYPE IF EXISTS source_type")


def downgrade() -> None:
    # Recreate ENUM types
    op.execute("""
        CREATE TYPE content_type AS ENUM (
            'note', 'conversation', 'quote', 'repo',
            'article', 'pdf', 'transcript', 'idea', 'reflection', 'log'
        )
    """)
    op.execute("""
        CREATE TYPE source_type AS ENUM (
            'manual', 'api', 'import', 'ocr', 'whisper', 'crawler'
        )
    """)

    op.execute("ALTER TABLE memory_records ALTER COLUMN content_type DROP DEFAULT")
    op.execute("ALTER TABLE memory_records ALTER COLUMN source_type DROP DEFAULT")

    op.execute("""
        ALTER TABLE memory_records
        ALTER COLUMN content_type TYPE content_type
        USING content_type::content_type
    """)
    op.execute("""
        ALTER TABLE memory_records
        ALTER COLUMN source_type TYPE source_type
        USING source_type::source_type
    """)

    op.execute("ALTER TABLE memory_records ALTER COLUMN content_type SET DEFAULT 'note'")
    op.execute("ALTER TABLE memory_records ALTER COLUMN source_type SET DEFAULT 'manual'")
