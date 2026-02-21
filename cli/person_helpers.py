"""
Person name helpers for CLI — suggest and normalize person names.

Rules:
- CLI never queries DB directly. Uses MemoryRepository.
- Person names are normalized to Title Case for consistency.
- Suggestion is simple substring match — no NLP, no fuzzy search.
"""

from app.memory.repository import MemoryRepository


def normalize_person_name(name: str) -> str:
    """Normalize a person name: strip whitespace, Title Case."""
    return name.strip().title()


def suggest_person_name(raw_text: str, existing_names: list[str]) -> list[str]:
    """
    Return existing person names that appear as substrings in raw_text.
    Simple, no NLP. Good enough for V1.
    """
    text_lower = raw_text.lower()
    return [name for name in existing_names if name.lower() in text_lower]


async def get_existing_person_names(repo: MemoryRepository) -> list[str]:
    """Fetch distinct person names from DB via repository layer."""
    return await repo.get_distinct_person_names()
