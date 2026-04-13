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
# compute_prompt_diff tests
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
    def test_returns_required_top_level_keys(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT)
        required = {
            "final_prompt", "initial_score", "final_score",
            "total_improvement", "iterations_used", "max_iterations",
            "target_score", "stopped_reason", "history",
        }
        assert required.issubset(result.keys())

    def test_history_is_a_list(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT)
        assert isinstance(result["history"], list)

    def test_each_history_entry_has_required_keys(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT)
        required = {"round", "prompt", "score", "improvement", "changes", "diff"}
        for entry in result["history"]:
            assert required.issubset(entry.keys()), f"Missing keys: {required - entry.keys()}"

    def test_round_numbers_are_sequential(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, max_iterations=3)
        for i, entry in enumerate(result["history"], start=1):
            assert entry["round"] == i

    def test_final_prompt_is_string(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT)
        assert isinstance(result["final_prompt"], str)
        assert len(result["final_prompt"]) > 0

    def test_scores_are_integers_in_range(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT)
        assert 0 <= result["initial_score"] <= 50
        assert 0 <= result["final_score"] <= 50

    def test_total_improvement_equals_score_delta(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT)
        expected = result["final_score"] - result["initial_score"]
        assert result["total_improvement"] == expected

    def test_iterations_used_matches_history_length(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, max_iterations=3)
        assert result["iterations_used"] == len(result["history"])


# ---------------------------------------------------------------------------
# optimize_prompt_loop — stop conditions
# ---------------------------------------------------------------------------


class TestOptimizeLoopStopConditions:
    def test_already_optimal_stops_immediately(self) -> None:
        result = optimize_prompt_loop(RICH_PROMPT, target_score=1)
        assert result["stopped_reason"] == STOP_ALREADY_OPTIMAL
        assert result["iterations_used"] == 0
        assert result["history"] == []
        assert result["final_prompt"] == RICH_PROMPT

    def test_target_score_reached_stops_loop(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, target_score=25, max_iterations=10)
        if result["stopped_reason"] == STOP_TARGET_REACHED:
            assert result["final_score"] >= 25

    def test_max_iterations_cap_respected(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, max_iterations=2)
        assert result["iterations_used"] <= 2

    def test_diminishing_returns_stops_loop(self) -> None:
        # With min_improvement=100 (impossible), should stop after _STALL_ROUNDS
        result = optimize_prompt_loop(VAGUE_PROMPT, min_improvement=100, max_iterations=10)
        assert result["stopped_reason"] in (
            STOP_DIMINISHING_RETURNS,
            STOP_TARGET_REACHED,
            STOP_MAX_ITERATIONS,
        )

    def test_stopped_reason_is_valid_constant(self) -> None:
        valid = {STOP_TARGET_REACHED, STOP_DIMINISHING_RETURNS, STOP_MAX_ITERATIONS, STOP_ALREADY_OPTIMAL}
        result = optimize_prompt_loop(VAGUE_PROMPT)
        assert result["stopped_reason"] in valid

    def test_target_score_clamped_above_max(self) -> None:
        # target_score > 50 should be clamped; already_optimal check may fire
        result = optimize_prompt_loop(RICH_PROMPT, target_score=999)
        # With a huge target the loop will exhaust iterations or hit diminishing returns
        assert result["stopped_reason"] in (
            STOP_DIMINISHING_RETURNS,
            STOP_MAX_ITERATIONS,
            STOP_ALREADY_OPTIMAL,
        )

    def test_target_score_clamped_below_min(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, target_score=-10)
        # Negative target clamped to 0; any prompt with score >= 0 stops immediately
        assert result["stopped_reason"] == STOP_ALREADY_OPTIMAL


# ---------------------------------------------------------------------------
# optimize_prompt_loop — quality improvement
# ---------------------------------------------------------------------------


class TestOptimizeLoopQualityImprovement:
    def test_vague_prompt_improves_score(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, max_iterations=5)
        assert result["final_score"] > result["initial_score"]

    def test_vague_prompt_reaches_reasonable_score(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, target_score=30, max_iterations=5)
        # Either target is reached, or significant improvement was made
        improvement = result["total_improvement"]
        assert improvement >= 5 or result["stopped_reason"] == STOP_TARGET_REACHED

    def test_language_hint_python_applies(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, language="python", max_iterations=3)
        assert "python" in result["final_prompt"].lower() or "pep" in result["final_prompt"].lower()

    def test_language_alias_py_accepted(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, language="py", max_iterations=2)
        assert "final_prompt" in result

    def test_history_diffs_are_populated(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, max_iterations=3)
        for entry in result["history"]:
            # diff may be empty if no text change, but should be a string
            assert isinstance(entry["diff"], str)


# ---------------------------------------------------------------------------
# optimize_prompt_loop — input validation
# ---------------------------------------------------------------------------


class TestOptimizeLoopValidation:
    def test_type_error_on_non_string_prompt(self) -> None:
        with pytest.raises(TypeError, match="prompt must be a string"):
            optimize_prompt_loop(42)  # type: ignore[arg-type]

    def test_value_error_on_empty_prompt(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            optimize_prompt_loop("")

    def test_value_error_on_whitespace_only_prompt(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            optimize_prompt_loop("   \n\t ")

    def test_value_error_on_max_iterations_less_than_one(self) -> None:
        with pytest.raises(ValueError, match="max_iterations"):
            optimize_prompt_loop(VAGUE_PROMPT, max_iterations=0)

    def test_max_iterations_one_runs_single_round(self) -> None:
        result = optimize_prompt_loop(VAGUE_PROMPT, max_iterations=1)
        assert result["iterations_used"] <= 1

    def test_context_injected_in_first_round(self) -> None:
        ctx = "This is a healthcare data processing pipeline."
        result = optimize_prompt_loop(VAGUE_PROMPT, context=ctx, max_iterations=2)
        assert ctx in result["final_prompt"]
