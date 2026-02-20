"""
Pydantic schemas for Memory endpoints.
These define the API contract — separate from ORM models.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class MemoryCreateRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Text content to store. Immutable after insert.")
    content_type: str = Field(default="note", description="One of: note, conversation, quote, repo, article, pdf, transcript, idea, reflection, log")
    source_type: str = Field(default="manual", description="One of: manual, api, import, ocr, whisper, crawler")
    importance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        allowed = {"note", "conversation", "quote", "repo", "article", "pdf", "transcript", "idea", "reflection", "log"}
        if v not in allowed:
            raise ValueError(f"content_type must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        allowed = {"manual", "api", "import", "ocr", "whisper", "crawler"}
        if v not in allowed:
            raise ValueError(f"source_type must be one of: {', '.join(sorted(allowed))}")
        return v


class MemoryResponse(BaseModel):
    id: uuid.UUID
    raw_text: str
    content_type: str
    source_type: str
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
