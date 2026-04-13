"""Stateful optimization session tools for agentic iterative prompt improvement."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.llm.base import LLMProvider
from src.tools.analyze_prompt import analyze_prompt
from src.tools.optimize_prompt import optimize_prompt
from src.tools.validation import validate_prompt

# ---------------------------------------------------------------------------
# Session store — in-memory, expires after SESSION_TTL seconds of inactivity
# ---------------------------------------------------------------------------

_SESSION_TTL: float = 1800.0  # 30 minutes

_sessions: dict[str, OptimizationSession] = {}


@dataclass
class OptimizationSession:
    """In-memory state for a single optimization session."""

    session_id: str
    current_prompt: str
    current_score: int
    iteration: int
    max_iterations: int
    target_score: int
    language: str | None
    history: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    @property
    def is_done(self) -> bool:
        """True when the session has nothing more to do."""
        return (
            self.current_score >= self.target_score
            or self.iteration >= self.max_iterations
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _purge_expired() -> None:
    """Remove sessions that have not been accessed within SESSION_TTL."""
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.last_active > _SESSION_TTL]
    for sid in expired:
        del _sessions[sid]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def start_optimization_session(
    task: str,
    max_iterations: int = 5,
    target_score: int = 80,
    language: str | None = None,
    context: str | None = None,
    provider: LLMProvider | None = None,
    llm_threshold: int = 80,
) -> dict[str, Any]:
    """Start a new iterative optimization session.

    Creates a session, runs the first optimization round, and returns a
    ``session_id`` that can be passed to :func:`continue_optimization_session`
    for subsequent rounds.

    Args:
        task: The raw prompt or task to optimize.
        max_iterations: Maximum number of rounds (default: 5).
        target_score: Normalized score (0-100) that signals "good enough" (default: 80).
        language: Optional programming language key for language-specific hints.
        context: Optional background context injected in the first round.
        provider: Optional :class:`LLMProvider` for hybrid optimization.
        llm_threshold: Normalized score threshold for LLM trigger (default: 80).

    Returns:
        A dict with keys:
            session_id (str): Use this to call continue_optimization_session.
            iteration (int): Always 1 for a new session.
            current_prompt (str): The prompt after the first optimization round.
            score_before (int): Raw score before any optimization.
            score_after (int): Raw score after round 1.
            score_normalized (int): Normalized score after round 1 (0-100).
            done (bool): True if target is already reached after round 1.
            reason (str): Reason for completion if done, else empty string.
            history (list): Per-round history so far.

    Raises:
        TypeError: If ``task`` is not a string.
        ValueError: If ``task`` is empty, whitespace-only, or too long.
    """
    validate_prompt(task, param_name="task")
    _purge_expired()

    session_id = str(uuid.uuid4())
    initial_analysis = analyze_prompt(task)
    initial_score: int = initial_analysis["total_score"]

    # Run round 1
    opt_result = await optimize_prompt(
        prompt=task,
        context=context,
        language=language,
        provider=provider,
        llm_threshold=llm_threshold,
    )
    new_prompt: str = opt_result["optimized_prompt"]
    new_score: int = opt_result["score_after"]
    score_normalized: int = opt_result["score_normalized_after"]

    history_entry: dict[str, Any] = {
        "round": 1,
        "prompt": new_prompt,
        "score": new_score,
        "score_normalized": score_normalized,
        "improvement": new_score - initial_score,
        "changes": opt_result["changes_summary"],
        "engine_used": opt_result["engine_used"],
    }

    session = OptimizationSession(
        session_id=session_id,
        current_prompt=new_prompt,
        current_score=new_score,
        iteration=1,
        max_iterations=max_iterations,
        target_score=target_score,
        language=language,
        history=[history_entry],
    )
    _sessions[session_id] = session

    done = session.is_done
    reason = ""
    if score_normalized >= target_score:
        reason = "target_score_reached"
    elif session.iteration >= max_iterations:
        reason = "max_iterations_reached"

    return {
        "session_id": session_id,
        "iteration": 1,
        "current_prompt": new_prompt,
        "score_before": initial_score,
        "score_after": new_score,
        "score_normalized": score_normalized,
        "done": done,
        "reason": reason,
        "history": [history_entry],
        "usage_hint": (
            "Call continue_optimization_session with this session_id "
            "to run the next optimization round."
            if not done
            else "Optimization complete. Use the current_prompt for your next task."
        ),
    }


async def continue_optimization_session(
    session_id: str,
    feedback: str | None = None,
    provider: LLMProvider | None = None,
    llm_threshold: int = 80,
) -> dict[str, Any]:
    """Continue an existing optimization session for one more round.

    Args:
        session_id: The session ID returned by :func:`start_optimization_session`.
        feedback: Optional text feedback from the agent. When provided, it is
                  appended as a context note before the next optimization round.
        provider: Optional :class:`LLMProvider` for hybrid optimization.
        llm_threshold: Normalized score threshold for LLM trigger (default: 80).

    Returns:
        A dict with keys:
            session_id (str): Same session ID.
            iteration (int): Round number just completed.
            current_prompt (str): The best prompt after this round.
            score_after (int): Raw score after this round.
            score_normalized (int): Normalized score (0-100).
            done (bool): True when session should end.
            reason (str): Why the session ended (or empty string if not done).
            history (list): All rounds so far.

    Raises:
        ValueError: If ``session_id`` is not found or the session has expired.
    """
    _purge_expired()

    session = _sessions.get(session_id)
    if session is None:
        raise ValueError(
            f"Session '{session_id}' not found or has expired. "
            "Start a new session with start_optimization_session."
        )

    if session.is_done:
        return {
            "session_id": session_id,
            "iteration": session.iteration,
            "current_prompt": session.current_prompt,
            "score_after": session.current_score,
            "score_normalized": round(session.current_score / 50 * 100),
            "done": True,
            "reason": "already_complete",
            "history": session.history,
            "usage_hint": "Session already complete. Use the current_prompt.",
        }

    session.last_active = time.time()
    context = f"Agent feedback: {feedback.strip()}" if feedback and feedback.strip() else None

    opt_result = await optimize_prompt(
        prompt=session.current_prompt,
        context=context,
        language=session.language,
        provider=provider,
        llm_threshold=llm_threshold,
    )
    new_prompt = opt_result["optimized_prompt"]
    new_score: int = opt_result["score_after"]
    score_normalized: int = opt_result["score_normalized_after"]

    session.iteration += 1
    session.current_prompt = new_prompt
    session.current_score = new_score

    history_entry = {
        "round": session.iteration,
        "prompt": new_prompt,
        "score": new_score,
        "score_normalized": score_normalized,
        "improvement": opt_result["score_after"] - opt_result["score_before"],
        "changes": opt_result["changes_summary"],
        "engine_used": opt_result["engine_used"],
        "feedback_used": feedback is not None,
    }
    session.history.append(history_entry)

    done = session.is_done
    reason = ""
    if score_normalized >= session.target_score:
        reason = "target_score_reached"
    elif session.iteration >= session.max_iterations:
        reason = "max_iterations_reached"

    return {
        "session_id": session_id,
        "iteration": session.iteration,
        "current_prompt": new_prompt,
        "score_after": new_score,
        "score_normalized": score_normalized,
        "done": done,
        "reason": reason,
        "history": session.history,
        "usage_hint": (
            "Call continue_optimization_session again for another round."
            if not done
            else "Optimization complete. Use the current_prompt for your next task."
        ),
    }
