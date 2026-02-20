"""
Pydantic schemas for Query (Reasoning) endpoints.
"""

import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question or prompt to reason over.")
    mode: str = Field(default="RECALL", description="One of: RECALL, REFLECT, CHALLENGE")
    content_type: Optional[str] = Field(default=None, description="Optional filter: restrict retrieval to this content type.")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    def validate_mode(self) -> "QueryRequest":
        valid = {"RECALL", "REFLECT", "CHALLENGE"}
        if self.mode not in valid:
            raise ValueError(f"mode must be one of: {', '.join(sorted(valid))}")
        return self


class QueryResponse(BaseModel):
    response: str
    mode: str
    memory_used: list[uuid.UUID]
    token_usage: dict[str, Any]
    external_knowledge_used: bool
    latency_ms: Optional[int] = None
