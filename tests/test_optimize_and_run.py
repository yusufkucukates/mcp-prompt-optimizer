"""Tests for the optimize_and_run meta-tool."""

from __future__ import annotations

import pytest

from src.tools.optimize_and_run import optimize_and_run


class TestOptimizeAndRun:
    async def test_returns_required_keys(self) -> None:
        result = await optimize_and_run(task="build a REST API for user management")
        required = {
            "optimized_task",
            "optimization_stats",
            "decomposition",
            "subtask_prompts",
            "language",
            "agent_type",
            "usage_hint",
        }
        assert required.issubset(result.keys())

    async def test_language_defaults_to_python(self) -> None:
        result = await optimize_and_run(task="write a script to process CSV files")
        assert result["language"] == "python"

    async def test_custom_language_respected(self) -> None:
        result = await optimize_and_run(task="write a REST API", language="typescript")
        assert result["language"] == "typescript"

    async def test_agent_type_defaults_to_code_agent(self) -> None:
        result = await optimize_and_run(task="implement a search feature")
        assert result["agent_type"] == "code_agent"

    async def test_subtask_prompts_list_not_empty(self) -> None:
        result = await optimize_and_run(task="implement a user auth service")
        assert len(result["subtask_prompts"]) > 0

    async def test_each_subtask_prompt_has_required_keys(self) -> None:
        result = await optimize_and_run(task="build a REST API for products")
        for item in result["subtask_prompts"]:
            assert "subtask_id" in item
            assert "title" in item
            assert "code_prompt" in item
            assert "usage_hint" in item

    async def test_optimized_task_is_longer_than_input(self) -> None:
        task = "make api"
        result = await optimize_and_run(task=task)
        assert len(result["optimized_task"]) > len(task)

    async def test_optimization_stats_has_scores(self) -> None:
        result = await optimize_and_run(task="build a cache layer")
        stats = result["optimization_stats"]
        assert "score_before" in stats
        assert "score_after" in stats
        assert "engine_used" in stats

    async def test_type_error_on_non_string_task(self) -> None:
        with pytest.raises(TypeError):
            await optimize_and_run(task=42)  # type: ignore[arg-type]

    async def test_value_error_on_empty_task(self) -> None:
        with pytest.raises(ValueError):
            await optimize_and_run(task="")
