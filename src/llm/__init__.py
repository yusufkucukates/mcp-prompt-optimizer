"""LLM enhancement layer for prompt-optimizer-mcp.

Provides a generic :class:`LLMProvider` interface with Anthropic and OpenAI
implementations.  All providers are optional dependencies — the server works
fully offline with the rule engine alone.
"""

from __future__ import annotations

from src.llm.base import LLMProvider, LLMResult
from src.llm.config import LLMConfig, get_config
from src.llm.factory import get_provider

__all__ = [
    "LLMConfig",
    "LLMProvider",
    "LLMResult",
    "get_config",
    "get_provider",
]
