"""
Pydantic schemas for Memory endpoints.
These define the API contract — separate from ORM models.

Memory Contract V1:
- content_type: 6 fixed values (note, conversation, reflection, idea, article, log)
- source info lives in metadata.source (not a top-level field)
- metadata structure: tags, type, source, source_urls, extra.person_name
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

# ─── Memory Contract V1: Fixed registries ────────────────────────────────────
VALID_CONTENT_TYPES = {"note", "conversation", "reflection", "idea", "article", "log"}


class MemoryCreateRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Text content to store. Immutable after insert.")
    content_type: str = Field(default="note", description="One of: note, conversation, reflection, idea, article, log")
    importance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        if v not in VALID_CONTENT_TYPES:
            raise ValueError(f"content_type must be one of: {', '.join(sorted(VALID_CONTENT_TYPES))}")
        return v


class MemoryResponse(BaseModel):
    id: uuid.UUID
    raw_text: str
    content_type: str
    checksum: str
    importance_score: Optional[float]
    metadata: dict[str, Any]
    is_archived: bool
    exclude_from_retrieval: bool
    is_summary: bool
    has_embedding: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryArchiveRequest(BaseModel):
    is_archived: bool = True
    exclude_from_retrieval: bool = False
