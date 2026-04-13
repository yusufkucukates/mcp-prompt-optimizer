"""Factory for creating an :class:`LLMProvider` from the current configuration."""

from __future__ import annotations

from src.llm.base import LLMProvider
from src.llm.config import LLMConfig, get_config


def get_provider(config: LLMConfig | None = None) -> LLMProvider | None:
    """Return the configured LLM provider, or ``None`` if LLM is disabled.

    Resolution order:
    1. If ``PROMPT_OPTIMIZER_LLM`` is not ``true`` (the default), return ``None``.
    2. If no API key is set, return ``None`` with a warning to stderr.
    3. If ``PROMPT_OPTIMIZER_PROVIDER`` is ``openai``, return :class:`OpenAIProvider`.
    4. Otherwise default to :class:`AnthropicProvider`.

    Args:
        config: Optional pre-built :class:`LLMConfig`. If ``None``, one is
                created from the current environment.

    Returns:
        A ready-to-use :class:`LLMProvider`, or ``None``.
    """
    import sys

    cfg = config if config is not None else get_config()

    if not cfg.enabled:
        return None

    if not cfg.api_key:
        print(
            "[prompt-optimizer] PROMPT_OPTIMIZER_LLM=true but no API key found. "
            "Set PROMPT_OPTIMIZER_API_KEY (or ANTHROPIC_API_KEY / OPENAI_API_KEY). "
            "Falling back to rule engine.",
            file=sys.stderr,
        )
        return None

    if cfg.provider == "openai":
        try:
            from src.llm.openai_provider import OpenAIProvider

            return OpenAIProvider(api_key=cfg.api_key, model=cfg.model)
        except ImportError:  # pragma: no cover
            print(
                "[prompt-optimizer] openai SDK not installed. "
                "Run: pip install prompt-optimizer-mcp[openai]",
                file=sys.stderr,
            )
            return None

    try:
        from src.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=cfg.api_key, model=cfg.model)
    except ImportError:  # pragma: no cover
        print(
            "[prompt-optimizer] anthropic SDK not installed. "
            "Run: pip install prompt-optimizer-mcp[anthropic]",
            file=sys.stderr,
        )
        return None
