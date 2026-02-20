"""
Personality loader — reads YAML personality files.
The personality system prompt is the foundation of all LLM interactions.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache(maxsize=4)
def load_personality(path: str = "personalities/default.yaml") -> dict[str, Any]:
    """
    Load and cache a YAML personality file.

    Returns a dict with at minimum:
        name: str
        tone: str
        language: str
        rules: list[str]
        constraints: list[str]
    """
    yaml_path = Path(path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Personality file not found: {path}")
    with yaml_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_system_prompt(personality: dict[str, Any]) -> str:
    """Convert personality dict into the system-level instruction block."""
    rules = "\n".join(f"- {r}" for r in personality.get("rules", []))
    constraints = "\n".join(f"- {c}" for c in personality.get("constraints", []))

    return (
        f"You are {personality.get('name', 'AI Person')}.\n"
        f"Tone: {personality.get('tone', 'direct, honest, analytical')}\n"
        f"Language: {personality.get('language', 'vi')}\n\n"
        f"Core Rules:\n{rules}\n\n"
        f"Constraints:\n{constraints}"
    )
