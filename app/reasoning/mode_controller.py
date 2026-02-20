"""
ModeController — selects mode instruction and policy for a given mode string.
Single-responsibility: knows about modes, nothing else.
"""

from app.core.prompts import MODE_INSTRUCTIONS, MODE_POLICIES, ModePolicy
from app.logging.logger import logger

VALID_MODES = frozenset({"RECALL", "REFLECT", "CHALLENGE"})


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

    def _validate(self, mode: str) -> str:
        mode = mode.upper().strip()
        if mode not in VALID_MODES:
            logger.warning("invalid_mode_fallback", extra={"requested": mode})
            return "RECALL"  # Safe default
        return mode
