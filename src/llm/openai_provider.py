"""OpenAI SDK wrapper for LLM prompt enhancement."""

from __future__ import annotations

import json

from src.llm.base import LLMProvider, LLMResult

# Lazy import — openai is an optional dependency
try:
    import openai as _openai_sdk  # type: ignore[import-not-found]

    _OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    _OPENAI_AVAILABLE = False


class OpenAIProvider(LLMProvider):
    """Uses ``openai.AsyncOpenAI`` to enhance prompts via GPT models.

    Args:
        api_key: OpenAI API key.
        model: Model identifier (e.g. ``gpt-4o-mini``).
        max_tokens: Maximum tokens in the completion (default 1024).
    """

    def __init__(self, api_key: str, model: str, max_tokens: int = 1024) -> None:
        if not _OPENAI_AVAILABLE:  # pragma: no cover
            raise ImportError(
                "The 'openai' package is required for the OpenAI provider. "
                "Install it with: pip install prompt-optimizer-mcp[openai]"
            )
        self._client = _openai_sdk.AsyncOpenAI(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def enhance_prompt(
        self,
        original: str,
        rule_output: str,
        weak_dimensions: list[str],
        scores: dict[str, int],
    ) -> LLMResult:
        """Call the OpenAI API and return the enhanced prompt.

        Falls back to ``rule_output`` on any API or JSON parsing error.
        """
        user_msg = self._build_user_message(original, rule_output, weak_dimensions, scores)
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = response.choices[0].message.content or "{}"
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
