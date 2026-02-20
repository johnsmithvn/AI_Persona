"""
TokenGuard — Context size management for the reasoning layer.

V1 Rules (Locked):
- No runtime summarization.
- Only use pre-computed summaries (is_summary=True).
- sort by final_score DESC, keep adding until budget exceeded, then drop.
"""

from dataclasses import dataclass
from typing import Any

from app.config import get_settings

settings = get_settings()


@dataclass
class BudgetedMemory:
    """Subset of memory fields needed for prompting."""
    id: str
    raw_text: str
    content_type: str
    created_at: Any
    importance_score: float
    final_score: float
    similarity: float
    is_summary: bool


class TokenGuard:
    """
    Manages token budget for memory context passed to LLM.

    Usage:
        guard = TokenGuard(token_counter=llm_adapter.count_tokens)
        trimmed = guard.check_budget(ranked_memories, max_tokens=3000)
    """

    def __init__(self, token_counter) -> None:
        """
        Args:
            token_counter: callable(text: str) → int
                           Typically LLMAdapter.count_tokens
        """
        self._count = token_counter

    def check_budget(
        self,
        memories: list[BudgetedMemory],
        max_tokens: int | None = None,
    ) -> list[BudgetedMemory]:
        """
        Select memories that fit within token budget.

        Args:
            memories: Already ranked list (descending final_score).
            max_tokens: Override budget. Uses settings.max_context_tokens if None.

        Returns:
            Subset of memories within token budget.
        """
        budget = max_tokens or settings.max_context_tokens
        selected: list[BudgetedMemory] = []
        total_tokens = 0

        for memory in sorted(memories, key=lambda m: m.final_score, reverse=True):
            tokens = self._count(memory.raw_text)
            if total_tokens + tokens > budget:
                break
            selected.append(memory)
            total_tokens += tokens

        return selected
