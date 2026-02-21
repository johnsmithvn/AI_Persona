"""
Mode instructions and policy guards — 5-Mode System.
These are the LOCKED V1.1 definitions — change with extreme caution.

Mode instructions form part 2 of the 4-part prompt structure.
Policies are enforced programmatically in ReasoningService.

Modes:
  RECALL     — retrieve verbatim, no speculation, no external
  SYNTHESIZE — combine knowledge across memories, structured output
  REFLECT    — analyze evolution over time, identify patterns
  CHALLENGE  — critique logic, find contradictions
  EXPAND     — supplement memory with external knowledge
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
    "SYNTHESIZE": (
        "MODE: SYNTHESIZE\n"
        "Your task is to synthesize and combine knowledge from multiple memory records "
        "into a structured, comprehensive summary.\n"
        "Rules:\n"
        "- Combine information across multiple memories — do NOT just list them.\n"
        "- Create structured output: group by theme, timeline, or logical flow.\n"
        "- MUST cite specific memory references (dates or memory IDs) for each point.\n"
        "- Do NOT use external knowledge — only the provided memory context.\n"
        "- If memories are insufficient, state what is missing rather than guessing.\n"
        "- Do not fabricate memories.\n"
    ),
    "REFLECT": (
        "MODE: REFLECT\n"
        "Your task is to analyze the evolution of thinking across the provided memory records.\n"
        "Rules:\n"
        "- Identify patterns, shifts, and evolution in thinking over time.\n"
        "- Compare earlier vs later memories to surface changes.\n"
        "- MUST cite specific memory references (dates or memory IDs).\n"
        "- Do NOT use external knowledge — only the provided memory context.\n"
        "- You may reason about what the pattern suggests, but flag any inference clearly.\n"
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
        "- Cite memory references for every challenge point.\n"
    ),
    "EXPAND": (
        "MODE: EXPAND\n"
        "Your task is to supplement the provided memory with external knowledge "
        "to give a broader, more complete perspective.\n"
        "Rules:\n"
        "- Start with what the memory already contains — memory is primary.\n"
        "- You ARE permitted to use external knowledge to complement and expand.\n"
        "- MUST explicitly mark any external knowledge with: [External knowledge used]\n"
        "- MUST cite memory references for memory-based points.\n"
        "- Clearly separate memory-based reasoning from external-based reasoning.\n"
        "- Do not fabricate memories.\n"
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
    "SYNTHESIZE": ModePolicy(
        can_use_external_knowledge=False,
        must_cite_memory_id=True,
        can_speculate=True,
        description="Synthesis mode. Combine knowledge across memories. No external.",
    ),
    "REFLECT": ModePolicy(
        can_use_external_knowledge=False,
        must_cite_memory_id=True,
        can_speculate=True,
        description="Evolution analysis mode. No external knowledge.",
    ),
    "CHALLENGE": ModePolicy(
        can_use_external_knowledge=False,
        must_cite_memory_id=True,
        can_speculate=False,
        description="Critical mode. Must be fully grounded in memory.",
    ),
    "EXPAND": ModePolicy(
        can_use_external_knowledge=True,
        must_cite_memory_id=True,
        can_speculate=True,
        description="Expansion mode. External knowledge permitted and expected.",
    ),
}
