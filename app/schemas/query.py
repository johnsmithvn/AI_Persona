"""
Pydantic schemas for Query (Reasoning) endpoints.
5-Mode System: RECALL, SYNTHESIZE, REFLECT, CHALLENGE, EXPAND
"""

import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ModeEnum(str, Enum):
    """Valid reasoning modes. Mode = permission system."""
    RECALL = "RECALL"
    SYNTHESIZE = "SYNTHESIZE"
    REFLECT = "REFLECT"
    CHALLENGE = "CHALLENGE"
    EXPAND = "EXPAND"


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question or prompt to reason over.")
    mode: ModeEnum = Field(
        default=ModeEnum.RECALL,
        description="Reasoning mode: RECALL, SYNTHESIZE, REFLECT, CHALLENGE, EXPAND",
    )
    content_type: Optional[str] = Field(
        default=None,
        description="Optional filter: restrict retrieval to this content type.",
    )
    threshold: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description=(
            "Cosine distance threshold (app-layer floor). "
            "Converted to similarity floor via similarity = 1 - distance. Lower = stricter."
        ),
    )

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {
            "note", "conversation", "quote", "repo", "article",
            "pdf", "transcript", "idea", "reflection", "log",
        }
        if v not in allowed:
            raise ValueError(f"content_type must be one of: {', '.join(sorted(allowed))}")
        return v


class QueryResponse(BaseModel):
    response: str
    mode: str
    memory_used: list[uuid.UUID]
    token_usage: dict[str, Any]
    external_knowledge_used: bool
    latency_ms: Optional[int] = None
