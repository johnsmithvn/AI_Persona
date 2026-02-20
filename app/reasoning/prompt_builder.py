"""
PromptBuilder — assembles the 4-part prompt structure.

4 Parts (DO NOT MIX):
  1. System Prompt    — personality (from YAML)
  2. Mode Instruction — RECALL / REFLECT / CHALLENGE behavior
  3. Memory Context   — retrieved records
  4. User Query       — the actual question

Order matters. Separation matters. Mixing = mode drift.
"""

from datetime import datetime
from typing import Any

from app.core.token_guard import BudgetedMemory


class PromptBuilder:
    """Builds a structured prompt from its 4 distinct parts."""

    MEMORY_TEMPLATE = "[Memory {index}] [{date}] (type={content_type}, score={score:.2f})\n{text}"

    def build(
        self,
        system_prompt: str,
        mode_instruction: str,
        memories: list[BudgetedMemory],
        user_query: str,
        external_knowledge_used: bool = False,
    ) -> str:
        """
        Assemble the full prompt string.

        Args:
            system_prompt: Built from personality YAML.
            mode_instruction: From ModeController.get_instruction().
            memories: Ranked memories within token budget.
            user_query: The user's original question.
            external_knowledge_used: If True, informs LLM it is allowed to use external knowledge.

        Returns:
            Single prompt string to send to LLMAdapter.generate().
        """
        parts = [
            "=== SYSTEM ===",
            system_prompt.strip(),
            "",
            "=== MODE ===",
            mode_instruction.strip(),
            "",
        ]

        if memories:
            parts.append("=== MEMORY CONTEXT ===")
            for i, m in enumerate(memories, start=1):
                date_str = m.created_at.strftime("%Y-%m-%d") if isinstance(m.created_at, datetime) else str(m.created_at)
                parts.append(self.MEMORY_TEMPLATE.format(
                    index=i,
                    date=date_str,
                    content_type=m.content_type,
                    score=m.similarity,
                    text=m.raw_text.strip(),
                ))
            parts.append("")
        else:
            parts.extend([
                "=== MEMORY CONTEXT ===",
                "[No relevant memories found for this query.]",
                "",
            ])

        if external_knowledge_used:
            parts.extend([
                "=== KNOWLEDGE NOTE ===",
                "You are permitted to supplement with external knowledge for this query.",
                "You MUST explicitly mark any external knowledge with: [External knowledge used]",
                "",
            ])

        parts.extend([
            "=== USER QUERY ===",
            user_query.strip(),
        ])

        return "\n".join(parts)
