"""
Mode instructions and policy guards.
These are the LOCKED V1 definitions — change with extreme caution.

Mode instructions form part 2 of the 4-part prompt structure.
Policies are enforced programmatically in ReasoningService.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModePolicy:
    """Constraints on LLM behavior for a given mode."""
    can_use_external_knowledge: bool
    must_cite_memory_id: bool
    can_speculate: bool
    description: str


# ─── Mode Instructions ────────────────────────────────────────────────────────
# These are injected verbatim into the prompt as part 2.

MODE_INSTRUCTIONS: dict[str, str] = {
    "RECALL": (
        "MODE: RECALL\n"
        "Your task is to retrieve and surface relevant information from the provided memory context.\n"
        "Rules:\n"
        "- Do NOT speculate or infer beyond what is explicitly written in the memory.\n"
        "- Do NOT use external knowledge — only the provided memory context.\n"
        "- If the memory context does not contain relevant information, say: "
        "\"Không có memory liên quan đến câu hỏi này.\"\n"
        "- Quote or closely paraphrase the memory when possible.\n"
        "- Cite the memory reference (date or position) when quoting.\n"
    ),
    "REFLECT": (
        "MODE: REFLECT\n"
        "Synthesize and analyze patterns across the provided memory records.\n"
        "Rules:\n"
        "- Identify evolution, patterns, and changes in thinking over time.\n"
        "- MUST cite specific memory references (dates or memory IDs).\n"
        "- You may use your reasoning to connect ideas, but flag any inference clearly.\n"
        "- If memory context is insufficient, you may supplement with general knowledge "
        "but MUST state: [External knowledge used]\n"
        "- Do not fabricate memories.\n"
    ),
    "CHALLENGE": (
        "MODE: CHALLENGE\n"
        "Your task is to critically evaluate and challenge the thinking in the provided memory.\n"
        "Rules:\n"
        "- Identify logical weaknesses, contradictions, or inconsistencies.\n"
        "- Base your challenge ENTIRELY on the provided memory — no external validation.\n"
        "- Do NOT soften contradictions. Be direct.\n"
        "- Do NOT agree just to be polite.\n"
        "- If no contradictions are found, say so explicitly.\n"
        "- Cite memory references for every Challenge point.\n"
    ),
}

# ─── Mode Policies ────────────────────────────────────────────────────────────

MODE_POLICIES: dict[str, ModePolicy] = {
    "RECALL": ModePolicy(
        can_use_external_knowledge=False,
        must_cite_memory_id=False,
        can_speculate=False,
        description="Strictly memory-bound retrieval. No external knowledge.",
    ),
    "REFLECT": ModePolicy(
        can_use_external_knowledge=True,
        must_cite_memory_id=True,
        can_speculate=True,
        description="Synthesis mode. External knowledge allowed only if flagged.",
    ),
    "CHALLENGE": ModePolicy(
        can_use_external_knowledge=False,
        must_cite_memory_id=True,
        can_speculate=False,
        description="Critical mode. Must be fully grounded in memory.",
    ),
}
