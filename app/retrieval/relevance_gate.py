"""
RelevanceGate — strict post-retrieval filtering for reasoning queries.

Goal:
- Avoid feeding "near-near" memories to reasoning modes.
- Prefer returning no-memory over weakly related context.
"""

from dataclasses import asdict, dataclass

from app.core.token_guard import BudgetedMemory


@dataclass(frozen=True)
class RelevanceGateConfig:
    min_top_similarity: float
    relative_drop: float
    max_results: int


@dataclass(frozen=True)
class RelevanceGateDecision:
    mode: str
    input_count: int
    output_count: int
    top_similarity: float
    cutoff_similarity: float
    rejected_all: bool

    def to_log(self) -> dict[str, float | int | str | bool]:
        return asdict(self)


_DEFAULT_CONFIG = RelevanceGateConfig(
    min_top_similarity=0.58,
    relative_drop=0.10,
    max_results=10,
)

_MODE_CONFIGS: dict[str, RelevanceGateConfig] = {
    # RECALL should be strictest and compact.
    "RECALL": RelevanceGateConfig(
        min_top_similarity=0.62,
        relative_drop=0.06,
        max_results=8,
    ),
    "SYNTHESIZE": RelevanceGateConfig(
        min_top_similarity=0.58,
        relative_drop=0.10,
        max_results=12,
    ),
    "REFLECT": RelevanceGateConfig(
        min_top_similarity=0.55,
        relative_drop=0.12,
        max_results=12,
    ),
    "CHALLENGE": RelevanceGateConfig(
        min_top_similarity=0.55,
        relative_drop=0.12,
        max_results=12,
    ),
    "EXPAND": RelevanceGateConfig(
        min_top_similarity=0.52,
        relative_drop=0.15,
        max_results=15,
    ),
}


def apply_relevance_gate(
    memories: list[BudgetedMemory],
    mode: str,
) -> tuple[list[BudgetedMemory], RelevanceGateDecision]:
    """
    Apply strict relevance gating.

    Formula:
      top = max(similarity_i)
      reject_all if top < min_top_similarity
      cutoff = max(min_top_similarity, top - relative_drop)
      keep i if similarity_i >= cutoff
      cap to max_results
    """
    normalized_mode = (mode or "").upper().strip()
    cfg = _MODE_CONFIGS.get(normalized_mode, _DEFAULT_CONFIG)

    if not memories:
        decision = RelevanceGateDecision(
            mode=normalized_mode or "UNKNOWN",
            input_count=0,
            output_count=0,
            top_similarity=0.0,
            cutoff_similarity=cfg.min_top_similarity,
            rejected_all=False,
        )
        return [], decision

    top_similarity = max(m.similarity for m in memories)
    if top_similarity < cfg.min_top_similarity:
        decision = RelevanceGateDecision(
            mode=normalized_mode or "UNKNOWN",
            input_count=len(memories),
            output_count=0,
            top_similarity=top_similarity,
            cutoff_similarity=cfg.min_top_similarity,
            rejected_all=True,
        )
        return [], decision

    cutoff_similarity = max(cfg.min_top_similarity, top_similarity - cfg.relative_drop)
    kept = [m for m in memories if m.similarity >= cutoff_similarity]
    kept = kept[: cfg.max_results]

    decision = RelevanceGateDecision(
        mode=normalized_mode or "UNKNOWN",
        input_count=len(memories),
        output_count=len(kept),
        top_similarity=top_similarity,
        cutoff_similarity=cutoff_similarity,
        rejected_all=False,
    )
    return kept, decision

