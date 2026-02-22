"""
ModeController — selects mode instruction and policy for a given mode string.
Single-responsibility: knows about modes, nothing else.

Modes: RECALL, RECALL_LLM_RERANK, SYNTHESIZE, REFLECT, CHALLENGE, EXPAND
"""

from app.core.prompts import MODE_INSTRUCTIONS, MODE_POLICIES, ModePolicy
from app.exceptions.handlers import InvalidModeError
from app.logging.logger import logger

VALID_MODES = frozenset(MODE_INSTRUCTIONS.keys())


class ModeController:
    """Maps mode strings to instructions and policies."""

    def get_instruction(self, mode: str) -> str:
        """Return the prompt instruction block for the given mode."""
        mode = self._validate(mode)
        return MODE_INSTRUCTIONS[mode]

    def get_policy(self, mode: str) -> ModePolicy:
        """Return the policy constraints for the given mode."""
        mode = self._validate(mode)
        return MODE_POLICIES[mode]

    @staticmethod
    def _validate(mode: str) -> str:
        """Validate and normalize mode string. Raises InvalidModeError on bad input."""
        mode = mode.upper().strip()
        if mode not in VALID_MODES:
            raise InvalidModeError(mode)
        return mode
