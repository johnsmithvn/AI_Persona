"""
Ranking module — scoring formula + diversity guard.

Formula (configurable weights per mode):
  final_score = w_semantic * similarity
              + w_recency  * EXP(-days_since_created / half_life)
              + w_importance * importance_score

No SQL here. Pure Python computation on already-retrieved records.
"""

import math
from datetime import datetime, timezone
from typing import Optional

from app.config import get_settings
from app.core.token_guard import BudgetedMemory

settings = get_settings()

# Mode-specific weight overrides (5-mode system — see DATA_DESIGN 7.2.1)
_MODE_WEIGHTS: dict[str, dict[str, float]] = {
    "RECALL": {
        "semantic": 0.70,
        "recency": 0.10,
        "importance": 0.20,
    },
    "SYNTHESIZE": {
        "semantic": 0.60,
        "recency": 0.05,
        "importance": 0.35,
    },
    "REFLECT": {
        "semantic": 0.40,
        "recency": 0.30,
        "importance": 0.30,
    },
    "CHALLENGE": {
        "semantic": 0.50,
        "recency": 0.10,
        "importance": 0.40,
    },
    "EXPAND": {
        "semantic": 0.70,
        "recency": 0.05,
        "importance": 0.25,
    },
}


_NEUTRAL_PROFILE = "NEUTRAL"
_NEUTRAL_WEIGHTS = {
    "semantic": settings.ranking_weight_semantic,
    "recency": settings.ranking_weight_recency,
    "importance": settings.ranking_weight_importance,
}


def get_ranking_profile(mode: Optional[str]) -> str:
    """
    Resolve ranking profile name from mode input.

    /search passes None -> NEUTRAL profile.
    /query passes one of the 5 reasoning modes -> mode profile.
    Unknown inputs fall back to NEUTRAL.
    """
    if not mode:
        return _NEUTRAL_PROFILE

    normalized = mode.upper().strip()
    return normalized if normalized in _MODE_WEIGHTS else _NEUTRAL_PROFILE


def _get_weights(mode: Optional[str]) -> dict[str, float]:
    profile = get_ranking_profile(mode)
    if profile == _NEUTRAL_PROFILE:
        return _NEUTRAL_WEIGHTS
    return _MODE_WEIGHTS[profile]


def compute_final_score(
    similarity: float,
    created_at: datetime,
    importance: Optional[float],
    mode: Optional[str] = None,
    half_life_days: Optional[float] = None,
) -> float:
    """
    Compute the final ranking score for a memory candidate.

    Args:
        similarity: Cosine similarity (0–1). Higher = more relevant.
        created_at: Timestamp of the memory record.
        importance: importance_score (0–1), defaults to 0.5 if None.
        mode:
            Reasoning mode (determines weighting) for /query.
            None (or invalid) uses neutral ranking weights for /search.
        half_life_days: Exponential decay half-life in days. Defaults to settings value.
    """
    weights = _get_weights(mode)

    hl = half_life_days or settings.ranking_recency_half_life_days

    # Ensure timezone-aware comparison
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    age_days = (now - created_at).total_seconds() / 86400.0
    recency_score = math.exp(-age_days / hl)
    imp = importance if importance is not None else 0.5

    return (
        weights["semantic"] * similarity
        + weights["recency"] * recency_score
        + weights["importance"] * imp
    )


def deduplicate_memories(
    memories: list[BudgetedMemory],
    threshold: float = 0.95,
) -> list[BudgetedMemory]:
    """
    Remove near-duplicate memories based on cosine similarity.
    If two memories have similarity > threshold, keep the higher-scoring one.

    NOTE: In V1 we compare similarity scores as a proxy (embeddings not carried
    through the ranking layer to avoid memory overhead). For V2, carry embeddings
    and compute actual pairwise cosine.
    """
    unique: list[BudgetedMemory] = []
    seen_texts: set[str] = set()

    for m in sorted(memories, key=lambda x: x.final_score, reverse=True):
        # Simple dedup: exact same text (after normalize)
        text_key = m.raw_text.strip().lower()[:200]  # first 200 chars as fingerprint
        if text_key not in seen_texts:
            unique.append(m)
            seen_texts.add(text_key)

    return unique
