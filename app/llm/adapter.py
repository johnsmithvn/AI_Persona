"""
Abstract LLMAdapter — all LLM implementations must satisfy this.
Adapter knows NOTHING about memory structure. Input: prompt → Output: response.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    """Per-request LLM configuration overrides."""
    temperature: float = 0.3
    max_tokens: int = 1000


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str


class LLMAdapter(ABC):
    """Abstract LLM interface."""

    @abstractmethod
    async def generate(self, prompt: str, config: Optional[LLMConfig] = None) -> LLMResponse:
        """Generate a response from the LLM given a full prompt string."""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string (for token budget management)."""
        ...
