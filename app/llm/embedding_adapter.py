"""
Abstract EmbeddingAdapter — all embedding implementations must satisfy this contract.
RetrievalService and EmbeddingWorker ONLY call this interface.
"""

from abc import ABC, abstractmethod


class EmbeddingAdapter(ABC):
    """Abstract embedding interface. Swap OpenAI → local model with zero upstream changes."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the canonical model identifier stored in memory_records.embedding_model."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return vector dimension (e.g. 1536)."""
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns float list of length `dimension`."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts. More efficient than calling embed() in a loop."""
        ...
