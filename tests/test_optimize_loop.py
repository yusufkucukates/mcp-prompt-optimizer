"""Tests for the iterative optimize_prompt_loop tool and diff_utils."""

from __future__ import annotations

import pytest

from src.tools.diff_utils import compute_prompt_diff
from src.tools.optimize_loop import (
    STOP_ALREADY_OPTIMAL,
    STOP_DIMINISHING_RETURNS,
    STOP_MAX_ITERATIONS,
    STOP_TARGET_REACHED,
    optimize_prompt_loop,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

VAGUE_PROMPT = "make an api for users"
RICH_PROMPT = (
    "You are a senior Python engineer. "
    "Implement a REST API endpoint using FastAPI that accepts a JSON body "
    "containing a user_id (integer) and returns a JSON object with the user profile. "
    "Use async/await for the database call. "
    "Return HTTP 404 with a clear error message if the user does not exist. "
    "Follow PEP 8 and add type hints to all functions."
)


# ---------------------------------------------------------------------------
# compute_prompt_diff tests (sync — diff_utils has no async code)
# ---------------------------------------------------------------------------


class TestComputePromptDiff:
    def test_identical_strings_return_empty(self) -> None:
        assert compute_prompt_diff("hello", "hello") == ""

    def test_changed_string_returns_diff(self) -> None:
        diff = compute_prompt_diff("line one\nline two", "line one\nline THREE")
        assert diff != ""
        assert "-line two" in diff
        assert "+line THREE" in diff

    def test_diff_has_plus_and_minus_markers(self) -> None:
        diff = compute_prompt_diff("old text", "new text")
        assert "+" in diff or "-" in diff

    def test_very_long_diff_is_truncated(self) -> None:
        long_before = "a\n" * 2000
        long_after = "b\n" * 2000
        diff = compute_prompt_diff(long_before, long_after)
        assert len(diff) <= 2100  # allow small overshoot for notice suffix
        assert "truncated" in diff

    def test_empty_before_produces_diff(self) -> None:
        diff = compute_prompt_diff("", "new content")
        assert "+" in diff

    def test_empty_after_produces_diff(self) -> None:
        diff = compute_prompt_diff("old content", "")
        assert "-" in diff


# ---------------------------------------------------------------------------
# optimize_prompt_loop — return structure
# ---------------------------------------------------------------------------


class TestOptimizeLoopReturnStructure:
    async def test_returns_required_top_level_keys(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT)
        required = {
            "final_prompt", "initial_score", "final_score",
            "total_improvement", "iterations_used", "max_iterations",
            "target_score", "stopped_reason", "history",
            "engine_used", "score_normalized_before", "score_normalized_after",
        }
        assert required.issubset(result.keys())

    async def test_engine_used_is_rules_without_provider(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT)
        assert result["engine_used"] == "rules"

    async def test_history_is_a_list(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT)
        assert isinstance(result["history"], list)

    async def test_each_history_entry_has_required_keys(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT)
        required = {"round", "prompt", "score", "improvement", "changes", "diff"}
        for entry in result["history"]:
            assert required.issubset(entry.keys()), f"Missing keys: {required - entry.keys()}"

    async def test_round_numbers_are_sequential(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, max_iterations=3)
        for i, entry in enumerate(result["history"], start=1):
            assert entry["round"] == i

    async def test_final_prompt_is_string(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT)
        assert isinstance(result["final_prompt"], str)
        assert len(result["final_prompt"]) > 0

    async def test_scores_are_integers_in_range(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT)
        assert 0 <= result["initial_score"] <= 50
        assert 0 <= result["final_score"] <= 50

    async def test_total_improvement_equals_score_delta(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT)
        expected = result["final_score"] - result["initial_score"]
        assert result["total_improvement"] == expected

    async def test_iterations_used_matches_history_length(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, max_iterations=3)
        assert result["iterations_used"] == len(result["history"])

    async def test_score_normalized_fields_present(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT)
        assert 0 <= result["score_normalized_before"] <= 100
        assert 0 <= result["score_normalized_after"] <= 100


# ---------------------------------------------------------------------------
# optimize_prompt_loop — stop conditions
# ---------------------------------------------------------------------------


class TestOptimizeLoopStopConditions:
    async def test_already_optimal_stops_immediately(self) -> None:
        result = await optimize_prompt_loop(RICH_PROMPT, target_score=1)
        assert result["stopped_reason"] == STOP_ALREADY_OPTIMAL
        assert result["iterations_used"] == 0
        assert result["history"] == []
        assert result["final_prompt"] == RICH_PROMPT

    async def test_target_score_reached_stops_loop(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, target_score=25, max_iterations=10)
        if result["stopped_reason"] == STOP_TARGET_REACHED:
            assert result["final_score"] >= 25

    async def test_max_iterations_cap_respected(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, max_iterations=2)
        assert result["iterations_used"] <= 2

    async def test_diminishing_returns_stops_loop(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, min_improvement=100, max_iterations=10)
        assert result["stopped_reason"] in (
            STOP_DIMINISHING_RETURNS,
            STOP_TARGET_REACHED,
            STOP_MAX_ITERATIONS,
        )

    async def test_stopped_reason_is_valid_constant(self) -> None:
        valid = {STOP_TARGET_REACHED, STOP_DIMINISHING_RETURNS, STOP_MAX_ITERATIONS, STOP_ALREADY_OPTIMAL}
        result = await optimize_prompt_loop(VAGUE_PROMPT)
        assert result["stopped_reason"] in valid

    async def test_target_score_clamped_above_max(self) -> None:
        result = await optimize_prompt_loop(RICH_PROMPT, target_score=999)
        assert result["stopped_reason"] in (
            STOP_DIMINISHING_RETURNS,
            STOP_MAX_ITERATIONS,
            STOP_ALREADY_OPTIMAL,
        )

    async def test_target_score_clamped_below_min(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, target_score=-10)
        assert result["stopped_reason"] == STOP_ALREADY_OPTIMAL


# ---------------------------------------------------------------------------
# optimize_prompt_loop — quality improvement
# ---------------------------------------------------------------------------


class TestOptimizeLoopQualityImprovement:
    async def test_vague_prompt_improves_score(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, max_iterations=5)
        assert result["final_score"] > result["initial_score"]

    async def test_vague_prompt_reaches_reasonable_score(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, target_score=30, max_iterations=5)
        improvement = result["total_improvement"]
        assert improvement >= 5 or result["stopped_reason"] == STOP_TARGET_REACHED

    async def test_language_hint_python_applies(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, language="python", max_iterations=3)
        assert "python" in result["final_prompt"].lower() or "pep" in result["final_prompt"].lower()

    async def test_language_alias_py_accepted(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, language="py", max_iterations=2)
        assert "final_prompt" in result

    async def test_history_diffs_are_populated(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, max_iterations=3)
        for entry in result["history"]:
            assert isinstance(entry["diff"], str)


# ---------------------------------------------------------------------------
# optimize_prompt_loop — input validation
# ---------------------------------------------------------------------------


class TestOptimizeLoopValidation:
    async def test_type_error_on_non_string_prompt(self) -> None:
        with pytest.raises(TypeError, match="prompt must be a string"):
            await optimize_prompt_loop(42)  # type: ignore[arg-type]

    async def test_value_error_on_empty_prompt(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            await optimize_prompt_loop("")

    async def test_value_error_on_whitespace_only_prompt(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            await optimize_prompt_loop("   \n\t ")

    async def test_value_error_on_max_iterations_less_than_one(self) -> None:
        with pytest.raises(ValueError, match="max_iterations"):
            await optimize_prompt_loop(VAGUE_PROMPT, max_iterations=0)

    async def test_max_iterations_one_runs_single_round(self) -> None:
        result = await optimize_prompt_loop(VAGUE_PROMPT, max_iterations=1)
        assert result["iterations_used"] <= 1

    async def test_context_injected_in_first_round(self) -> None:
        ctx = "This is a healthcare data processing pipeline."
        result = await optimize_prompt_loop(VAGUE_PROMPT, context=ctx, max_iterations=2)
        assert ctx in result["final_prompt"]
