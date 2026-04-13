"""Anthropic SDK wrapper for LLM prompt enhancement."""

from __future__ import annotations

import json

from src.llm.base import LLMProvider, LLMResult

# Lazy import — anthropic is an optional dependency
try:
    import anthropic as _anthropic_sdk  # type: ignore[import-not-found]

    _ANTHROPIC_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ANTHROPIC_AVAILABLE = False


class AnthropicProvider(LLMProvider):
    """Uses ``anthropic.AsyncAnthropic`` to enhance prompts via Claude.

    Args:
        api_key: Anthropic API key.
        model: Claude model identifier (e.g. ``claude-haiku-4-20250514``).
        max_tokens: Maximum tokens in the completion (default 1024).
    """

    def __init__(self, api_key: str, model: str, max_tokens: int = 1024) -> None:
        if not _ANTHROPIC_AVAILABLE:  # pragma: no cover
            raise ImportError(
                "The 'anthropic' package is required for the Anthropic provider. "
                "Install it with: pip install prompt-optimizer-mcp[anthropic]"
            )
        self._client = _anthropic_sdk.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def enhance_prompt(
        self,
        original: str,
        rule_output: str,
        weak_dimensions: list[str],
        scores: dict[str, int],
    ) -> LLMResult:
        """Call the Anthropic API and return the enhanced prompt.

        Falls back to ``rule_output`` on any API or JSON parsing error.
        """
        user_msg = self._build_user_message(original, rule_output, weak_dimensions, scores)
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=self._build_system_prompt(),
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text
            data: dict[str, str] = json.loads(raw)
            return LLMResult(
                enhanced_prompt=data.get("enhanced_prompt", rule_output),
                explanation=data.get("explanation", ""),
                model_used=self._model,
            )
        except Exception:
            return LLMResult(
                enhanced_prompt=rule_output,
                explanation="LLM call failed; rule-engine output used.",
                model_used=self._model,
            )
