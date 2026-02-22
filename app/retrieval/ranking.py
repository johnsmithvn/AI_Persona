"""
Ranking module — scoring formula + diversity guard.

Formula (configurable weights per mode):
  final_score = w_semantic * similarity
              + w_recency  * EXP(-days_since_created / half_life)
              + w_importance * importance_score

No SQL here. Pure Python computation on already-retrieved records.
"""

import math
import re
import unicodedata
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

_LEXICAL_MODES = {"RECALL", "CHALLENGE"}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "toi", "tao", "ban", "anh", "chi", "em", "se", "da", "dang", "duoc",
    "la", "thi", "va", "hoac", "nhung", "cho", "voi", "tren", "duoi", "nay",
    "kia", "day", "do", "ma", "tu", "den", "roi", "thoi",
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


def _normalize_for_match(text: str) -> str:
    """Lowercase + strip accents for lightweight lexical matching."""
    lowered = text.lower()
    normalized = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_marks


def _extract_query_keywords(query: str) -> list[str]:
    normalized = _normalize_for_match(query)
    tokens = _TOKEN_PATTERN.findall(normalized)
    return [t for t in tokens if len(t) >= 4 and t not in _STOPWORDS]


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


def compute_exposure_diversity_bonus(
    retrieval_count: int,
    *,
    weight: Optional[float] = None,
    max_bonus: Optional[float] = None,
) -> float:
    """
    Compute a small bonus for under-exposed memories.

    Formula:
      diversity = 1 / (1 + retrieval_count)
      bonus = weight * diversity

    Notes:
    - retrieval_count = number of past reasoning sessions that used this memory.
    - bonus must stay small so semantic relevance still dominates.
    """
    w = settings.ranking_diversity_weight if weight is None else weight
    if w <= 0:
        return 0.0

    safe_count = max(0, retrieval_count)
    diversity = 1.0 / (1.0 + float(safe_count))
    bonus = w * diversity

    cap = settings.ranking_diversity_bonus_cap if max_bonus is None else max_bonus
    if cap <= 0:
        return bonus
    return min(cap, bonus)


def compute_query_lexical_bonus(
    query: str,
    memory_text: str,
    mode: Optional[str],
) -> float:
    """
    Boost memories that explicitly mention key query terms.

    Applied only for RECALL/CHALLENGE where users expect direct phrase hits.
    """
    if not query or not memory_text:
        return 0.0

    normalized_mode = (mode or "").upper().strip()
    if normalized_mode not in _LEXICAL_MODES:
        return 0.0

    keywords = _extract_query_keywords(query)
    if not keywords:
        return 0.0

    normalized_text = _normalize_for_match(memory_text)
    matched = sum(1 for token in keywords if token in normalized_text)
    if matched == 0:
        return 0.0

    ratio = matched / float(len(keywords))
    bonus = 0.0
    if matched >= 2:
        bonus += 0.03
    if ratio >= 0.5:
        bonus += 0.03
    if ratio >= 0.8:
        bonus += 0.02
    return min(0.08, bonus)


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
