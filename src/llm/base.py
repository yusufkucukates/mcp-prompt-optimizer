"""Abstract base for LLM enhancement providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    """Result returned by any LLM provider."""

    enhanced_prompt: str
    explanation: str
    model_used: str


class LLMProvider(ABC):
    """Abstract LLM provider interface.

    Concrete implementations wrap a specific SDK (Anthropic, OpenAI, etc.)
    and translate the generic :meth:`enhance_prompt` contract into the
    appropriate API call.
    """

    @abstractmethod
    async def enhance_prompt(
        self,
        original: str,
        rule_output: str,
        weak_dimensions: list[str],
        scores: dict[str, int],
    ) -> LLMResult:
        """Improve a prompt using an LLM, focused on the weakest dimensions.

        Args:
            original: The raw prompt text before any optimization.
            rule_output: The prompt after rule-engine optimization.
            weak_dimensions: Names of dimensions that scored below the threshold.
            scores: Per-dimension scores from the rule engine analysis.

        Returns:
            An :class:`LLMResult` with the enhanced prompt and change explanation.
        """

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "You are a world-class prompt engineering expert specializing in prompts "
            "for AI coding agents and developer tools. "
            "Your task: improve the given prompt to make it clearer, more specific, "
            "and immediately actionable for an AI coding agent. "
            "Rules:\n"
            "- Keep changes minimal and purposeful — do not add padding or verbosity.\n"
            "- Preserve the original intent exactly.\n"
            "- Focus only on the weak dimensions listed in the user message.\n"
            "- Do NOT add comments, explanations, or markdown formatting to the prompt itself.\n"
            "- Return ONLY a JSON object with two keys: "
            '"enhanced_prompt" (the improved prompt as a single string) and '
            '"explanation" (1-2 sentences describing what changed and why).'
        )

    @staticmethod
    def _build_user_message(
        original: str,
        rule_output: str,
        weak_dimensions: list[str],
        scores: dict[str, int],
    ) -> str:
        score_lines = "\n".join(f"  {dim}: {score}/10" for dim, score in scores.items())
        weak_str = ", ".join(weak_dimensions) if weak_dimensions else "none"
        return (
            f"## Original prompt\n{original}\n\n"
            f"## After rule-engine optimization\n{rule_output}\n\n"
            f"## Current dimension scores\n{score_lines}\n\n"
            f"## Weak dimensions to improve: {weak_str}\n\n"
            "Improve the rule-engine output to address the weak dimensions. "
            "Return the result as a JSON object with keys 'enhanced_prompt' and 'explanation'."
        )
