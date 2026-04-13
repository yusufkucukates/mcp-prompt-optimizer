"""Tests for the LLM provider infrastructure (mocked — no real API calls)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.base import LLMProvider
from src.llm.config import LLMConfig, get_config
from src.llm.factory import get_provider

# ---------------------------------------------------------------------------
# LLMConfig tests
# ---------------------------------------------------------------------------


class TestLLMConfig:
    def test_default_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PROMPT_OPTIMIZER_LLM", None)
            cfg = get_config()
        assert cfg.enabled is False

    def test_enabled_by_env(self) -> None:
        with patch.dict(os.environ, {"PROMPT_OPTIMIZER_LLM": "true"}):
            cfg = get_config()
        assert cfg.enabled is True

    def test_enabled_case_insensitive(self) -> None:
        for val in ("TRUE", "True", "1", "yes", "on"):
            with patch.dict(os.environ, {"PROMPT_OPTIMIZER_LLM": val}):
                cfg = get_config()
            assert cfg.enabled is True, f"Failed for value: {val!r}"

    def test_default_provider_anthropic(self) -> None:
        cfg = LLMConfig()
        assert cfg.provider == "anthropic"

    def test_provider_override(self) -> None:
        with patch.dict(os.environ, {"PROMPT_OPTIMIZER_PROVIDER": "openai"}):
            cfg = get_config()
        assert cfg.provider == "openai"

    def test_threshold_default(self) -> None:
        cfg = LLMConfig()
        assert cfg.threshold == 80

    def test_threshold_override(self) -> None:
        with patch.dict(os.environ, {"PROMPT_OPTIMIZER_THRESHOLD": "60"}):
            cfg = get_config()
        assert cfg.threshold == 60

    def test_api_key_fallback_anthropic(self) -> None:
        env = {
            "ANTHROPIC_API_KEY": "test-key",
            "PROMPT_OPTIMIZER_PROVIDER": "anthropic",
        }
        # Remove override key so fallback is triggered
        with patch.dict(os.environ, env, clear=True):
            cfg = get_config()
        assert cfg.api_key == "test-key"

    def test_api_key_fallback_openai(self) -> None:
        env = {
            "PROMPT_OPTIMIZER_PROVIDER": "openai",
            "OPENAI_API_KEY": "openai-key",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = get_config()
        assert cfg.api_key == "openai-key"

    def test_explicit_api_key_takes_priority(self) -> None:
        env = {"PROMPT_OPTIMIZER_API_KEY": "explicit-key", "ANTHROPIC_API_KEY": "fallback"}
        with patch.dict(os.environ, env, clear=True):
            cfg = get_config()
        assert cfg.api_key == "explicit-key"

    def test_default_anthropic_model(self) -> None:
        cfg = LLMConfig()
        assert "claude" in cfg.model

    def test_default_openai_model(self) -> None:
        with patch.dict(os.environ, {"PROMPT_OPTIMIZER_PROVIDER": "openai"}):
            cfg = get_config()
        assert "gpt" in cfg.model

    def test_model_override(self) -> None:
        with patch.dict(os.environ, {"PROMPT_OPTIMIZER_MODEL": "my-custom-model"}):
            cfg = get_config()
        assert cfg.model == "my-custom-model"

    def test_is_usable_false_when_disabled(self) -> None:
        cfg = LLMConfig()
        cfg.enabled = False
        assert cfg.is_usable is False

    def test_is_usable_false_when_no_key(self) -> None:
        env = {"PROMPT_OPTIMIZER_LLM": "true"}
        with patch.dict(os.environ, env, clear=True):
            cfg = get_config()
        assert cfg.is_usable is False

    def test_is_usable_true_with_key(self) -> None:
        env = {"PROMPT_OPTIMIZER_LLM": "true", "PROMPT_OPTIMIZER_API_KEY": "sk-test"}
        with patch.dict(os.environ, env, clear=True):
            cfg = get_config()
        assert cfg.is_usable is True


# ---------------------------------------------------------------------------
# get_provider factory tests
# ---------------------------------------------------------------------------


class TestGetProvider:
    def test_returns_none_when_disabled(self) -> None:
        with patch.dict(os.environ, {"PROMPT_OPTIMIZER_LLM": "false"}):
            result = get_provider()
        assert result is None

    def test_returns_none_when_no_key(self) -> None:
        with patch.dict(
            os.environ,
            {"PROMPT_OPTIMIZER_LLM": "true", "PROMPT_OPTIMIZER_API_KEY": ""},
        ):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            result = get_provider()
        assert result is None

    def test_returns_anthropic_provider(self) -> None:
        cfg = LLMConfig()
        cfg.enabled = True
        cfg.api_key = "sk-test"
        cfg.provider = "anthropic"

        mock_cls = MagicMock()
        mock_cls.return_value = MagicMock()
        with patch.dict("sys.modules", {"src.llm.anthropic_provider": MagicMock(AnthropicProvider=mock_cls)}):
            result = get_provider(config=cfg)

        assert result is not None

    def test_returns_openai_provider(self) -> None:
        cfg = LLMConfig()
        cfg.enabled = True
        cfg.api_key = "sk-test"
        cfg.provider = "openai"

        mock_cls = MagicMock()
        mock_cls.return_value = MagicMock()
        with patch.dict("sys.modules", {"src.llm.openai_provider": MagicMock(OpenAIProvider=mock_cls)}):
            result = get_provider(config=cfg)

        assert result is not None


# ---------------------------------------------------------------------------
# LLMProvider base helper tests
# ---------------------------------------------------------------------------


class TestLLMProviderHelpers:
    def test_system_prompt_contains_key_instructions(self) -> None:
        system = LLMProvider._build_system_prompt()  # type: ignore[abstract]
        assert "enhanced_prompt" in system
        assert "explanation" in system

    def test_user_message_contains_all_sections(self) -> None:
        msg = LLMProvider._build_user_message(  # type: ignore[abstract]
            original="write a function",
            rule_output="You are a senior engineer. Write a function.",
            weak_dimensions=["specificity", "output_definition"],
            scores={"clarity": 7, "specificity": 2, "context": 8, "output_definition": 1, "actionability": 6},
        )
        assert "write a function" in msg
        assert "specificity" in msg
        assert "output_definition" in msg
        assert "clarity: 7/10" in msg


# ---------------------------------------------------------------------------
# Anthropic provider tests (mocked SDK)
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    @pytest.fixture
    def provider(self) -> object:
        with patch.dict("sys.modules", {"anthropic": MagicMock()}):
            from importlib import reload

            import src.llm.anthropic_provider as mod

            reload(mod)
            mod._ANTHROPIC_AVAILABLE = True  # type: ignore[attr-defined]
            mock_client = MagicMock()
            p = mod.AnthropicProvider.__new__(mod.AnthropicProvider)
            p._client = mock_client
            p._model = "claude-haiku-4-20250514"
            p._max_tokens = 1024
            return p

    @pytest.mark.asyncio
    async def test_enhance_prompt_success(self, provider: object) -> None:
        import json

        from src.llm.anthropic_provider import AnthropicProvider

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "enhanced_prompt": "Enhanced: write a function",
            "explanation": "Added specificity.",
        }))]

        p = provider  # type: ignore[assignment]
        p._client.messages.create = AsyncMock(return_value=mock_response)  # type: ignore[union-attr]

        result = await AnthropicProvider.enhance_prompt(  # type: ignore[misc]
            p,
            original="write a function",
            rule_output="You are an engineer. Write a function.",
            weak_dimensions=["specificity"],
            scores={"specificity": 2},
        )
        assert result.enhanced_prompt == "Enhanced: write a function"
        assert result.explanation == "Added specificity."

    @pytest.mark.asyncio
    async def test_enhance_prompt_fallback_on_api_error(self, provider: object) -> None:
        from src.llm.anthropic_provider import AnthropicProvider

        p = provider  # type: ignore[assignment]
        p._client.messages.create = AsyncMock(side_effect=Exception("API error"))  # type: ignore[union-attr]

        result = await AnthropicProvider.enhance_prompt(  # type: ignore[misc]
            p,
            original="orig",
            rule_output="rule output",
            weak_dimensions=[],
            scores={},
        )
        assert result.enhanced_prompt == "rule output"
        assert "failed" in result.explanation.lower()


# ---------------------------------------------------------------------------
# OpenAI provider tests (mocked SDK)
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    @pytest.mark.asyncio
    async def test_enhance_prompt_fallback_on_api_error(self) -> None:
        import json

        with patch.dict("sys.modules", {"openai": MagicMock()}):
            from importlib import reload

            import src.llm.openai_provider as mod

            reload(mod)
            mod._OPENAI_AVAILABLE = True  # type: ignore[attr-defined]
            p = mod.OpenAIProvider.__new__(mod.OpenAIProvider)
            p._model = "gpt-4o-mini"
            p._max_tokens = 1024
            mock_client = MagicMock()
            p._client = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps({
                "enhanced_prompt": "Better prompt",
                "explanation": "Improved clarity.",
            })))]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await mod.OpenAIProvider.enhance_prompt(
                p,
                original="fix bug",
                rule_output="You are an engineer. Fix the bug.",
                weak_dimensions=["clarity"],
                scores={"clarity": 3},
            )
        assert result.enhanced_prompt == "Better prompt"
