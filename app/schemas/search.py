"""
Pydantic schemas for Search endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.memory import VALID_CONTENT_TYPES


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query.")
    content_type: Optional[str] = Field(default=None, description="Filter by content type.")
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)
    limit: int = Field(default=20, ge=1, le=100)
    threshold: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description=(
            "Cosine distance threshold (app-layer floor). "
            "Converted to similarity floor via similarity = 1 - distance."
        ),
    )
    metadata_filter: Optional[dict[str, Any]] = Field(default=None, description="JSONB filter, e.g. {'tags': ['ai']}")
    include_summaries: bool = Field(default=False, description="Include is_summary=true records.")

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_CONTENT_TYPES:
            raise ValueError(f"content_type must be one of: {', '.join(sorted(VALID_CONTENT_TYPES))}")
        return v


class MemorySearchResult(BaseModel):
    id: uuid.UUID
    raw_text: str
    content_type: str
    importance_score: Optional[float]
    created_at: datetime
    metadata: dict[str, Any]
    similarity: float
    final_score: float
    is_summary: bool

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    results: list[MemorySearchResult]
    total: int
    query: str
    ranking_profile: str = Field(
        default="NEUTRAL",
        description="Ranking profile used for final_score calculation. /search always returns NEUTRAL.",
    )
