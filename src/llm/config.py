"""Environment-variable configuration for the LLM enhancement layer."""

from __future__ import annotations

import os


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, "").strip().lower()
    if not val:
        return default
    return val in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key, "").strip()
    try:
        return int(val) if val else default
    except ValueError:
        return default


class LLMConfig:
    """Reads LLM configuration from environment variables.

    Environment variables:
        PROMPT_OPTIMIZER_LLM       Enable LLM layer (true/false, default: false).
        PROMPT_OPTIMIZER_PROVIDER  Provider name: anthropic | openai (default: anthropic).
        PROMPT_OPTIMIZER_API_KEY   API key. Falls back to ANTHROPIC_API_KEY or OPENAI_API_KEY.
        PROMPT_OPTIMIZER_MODEL     Override default model name.
        PROMPT_OPTIMIZER_THRESHOLD Normalized score (0-100) below which LLM triggers (default: 80).
    """

    def __init__(self) -> None:
        self.enabled: bool = _env_bool("PROMPT_OPTIMIZER_LLM", default=False)
        self.provider: str = os.environ.get("PROMPT_OPTIMIZER_PROVIDER", "anthropic").strip().lower()
        self.threshold: int = _env_int("PROMPT_OPTIMIZER_THRESHOLD", default=80)
        self._model_override: str = os.environ.get("PROMPT_OPTIMIZER_MODEL", "").strip()

        # Resolve API key eagerly at construction time so callers see a
        # consistent value regardless of later environment changes.
        explicit = os.environ.get("PROMPT_OPTIMIZER_API_KEY", "").strip()
        if explicit:
            self.api_key: str = explicit
        elif self.provider == "openai":
            self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        else:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    @property
    def model(self) -> str:
        """Return the model name, falling back to a sensible per-provider default."""
        if self._model_override:
            return self._model_override
        if self.provider == "openai":
            return "gpt-4o-mini"
        return "claude-haiku-4-20250514"

    @property
    def is_usable(self) -> bool:
        """True only when LLM is enabled, a key is set, and a provider is chosen."""
        return (
            self.enabled
            and bool(self.api_key)
            and self.provider in ("anthropic", "openai")
        )


# Module-level singleton — re-read on every module import so that tests
# can patch env vars without special tricks.
def get_config() -> LLMConfig:
    """Return a fresh :class:`LLMConfig` built from the current environment."""
    return LLMConfig()
