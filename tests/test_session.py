"""Tests for the stateful optimization session tools."""

from __future__ import annotations

import pytest

from src.tools.session import (
    _sessions,
    continue_optimization_session,
    start_optimization_session,
)


class TestStartOptimizationSession:
    async def test_returns_required_keys(self) -> None:
        result = await start_optimization_session(task="write a cache module")
        required = {
            "session_id",
            "iteration",
            "current_prompt",
            "score_before",
            "score_after",
            "score_normalized",
            "done",
            "reason",
            "history",
            "usage_hint",
        }
        assert required.issubset(result.keys())

    async def test_session_id_is_string(self) -> None:
        result = await start_optimization_session(task="build an auth service")
        assert isinstance(result["session_id"], str)
        assert len(result["session_id"]) > 0

    async def test_iteration_is_one(self) -> None:
        result = await start_optimization_session(task="implement pagination")
        assert result["iteration"] == 1

    async def test_history_has_one_entry(self) -> None:
        result = await start_optimization_session(task="write unit tests")
        assert len(result["history"]) == 1

    async def test_session_stored_in_memory(self) -> None:
        result = await start_optimization_session(task="add a health endpoint")
        assert result["session_id"] in _sessions

    async def test_score_normalized_is_0_to_100(self) -> None:
        result = await start_optimization_session(task="refactor the database layer")
        assert 0 <= result["score_normalized"] <= 100

    async def test_done_false_for_vague_task(self) -> None:
        result = await start_optimization_session(task="do stuff", target_score=95)
        assert result["done"] is False

    async def test_type_error_on_non_string_task(self) -> None:
        with pytest.raises(TypeError):
            await start_optimization_session(task=123)  # type: ignore[arg-type]

    async def test_value_error_on_empty_task(self) -> None:
        with pytest.raises(ValueError):
            await start_optimization_session(task="")


class TestContinueOptimizationSession:
    async def test_continue_increments_iteration(self) -> None:
        start = await start_optimization_session(task="implement a rate limiter", target_score=95)
        sid = start["session_id"]
        cont = await continue_optimization_session(session_id=sid)
        assert cont["iteration"] == 2

    async def test_continue_history_grows(self) -> None:
        start = await start_optimization_session(task="write a data export tool", target_score=95)
        sid = start["session_id"]
        cont = await continue_optimization_session(session_id=sid)
        assert len(cont["history"]) == 2

    async def test_continue_with_feedback(self) -> None:
        start = await start_optimization_session(task="add logging to the API", target_score=95)
        sid = start["session_id"]
        cont = await continue_optimization_session(
            session_id=sid, feedback="Focus on structured JSON logs only."
        )
        assert cont["history"][-1].get("feedback_used") is True

    async def test_invalid_session_id_raises(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            await continue_optimization_session(session_id="nonexistent-session")

    async def test_done_when_max_iterations_reached(self) -> None:
        start = await start_optimization_session(task="refactor code", max_iterations=1, target_score=99)
        sid = start["session_id"]
        if not start["done"]:
            # Should be done after one more continue since max_iterations=1
            cont = await continue_optimization_session(session_id=sid)
            assert cont["done"] is True

    async def test_returns_same_session_id(self) -> None:
        start = await start_optimization_session(task="write integration tests", target_score=95)
        sid = start["session_id"]
        cont = await continue_optimization_session(session_id=sid)
        assert cont["session_id"] == sid
