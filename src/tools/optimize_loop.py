"""Iterative prompt optimisation loop: runs multiple rounds of optimization
until a quality target is reached, diminishing returns are detected, or the
maximum iteration cap is hit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.tools.analyze_prompt import analyze_prompt
from src.tools.diff_utils import compute_prompt_diff
from src.tools.optimize_prompt import optimize_prompt

# ---------------------------------------------------------------------------
# Stop-reason constants (used in the returned dict and in tests)
# ---------------------------------------------------------------------------

STOP_TARGET_REACHED = "target_score_reached"
STOP_DIMINISHING_RETURNS = "diminishing_returns"
STOP_MAX_ITERATIONS = "max_iterations"
STOP_ALREADY_OPTIMAL = "already_optimal"

# How many consecutive low-improvement rounds before we declare diminishing returns
_STALL_ROUNDS = 2

# Score range bounds
_SCORE_MIN = 0
_SCORE_MAX = 50


# ---------------------------------------------------------------------------
# Internal data models
# ---------------------------------------------------------------------------


@dataclass
class LoopIteration:
    """Result of a single optimisation round inside the loop."""

    round: int
    prompt: str
    score: int
    improvement: int
    changes: list[str]
    diff: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "round": self.round,
            "prompt": self.prompt,
            "score": self.score,
            "improvement": self.improvement,
            "changes": self.changes,
            "diff": self.diff,
        }


@dataclass
class LoopResult:
    """Complete result of an optimisation loop run."""

    final_prompt: str
    initial_score: int
    final_score: int
    total_improvement: int
    iterations_used: int
    max_iterations: int
    target_score: int
    stopped_reason: str
    history: list[LoopIteration] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_prompt": self.final_prompt,
            "initial_score": self.initial_score,
            "final_score": self.final_score,
            "total_improvement": self.total_improvement,
            "iterations_used": self.iterations_used,
            "max_iterations": self.max_iterations,
            "target_score": self.target_score,
            "stopped_reason": self.stopped_reason,
            "history": [it.to_dict() for it in self.history],
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def optimize_prompt_loop(
    prompt: str,
    language: str | None = None,
    context: str | None = None,
    target_score: int = 40,
    max_iterations: int = 5,
    min_improvement: int = 2,
) -> dict[str, Any]:
    """Iteratively optimise a prompt until it is "good enough".

    Runs repeated rounds of :func:`optimize_prompt` and
    :func:`analyze_prompt`, stopping as soon as **any** of the three
    termination conditions is met:

    1. ``score >= target_score`` — quality goal achieved.
    2. ``improvement < min_improvement`` for ``_STALL_ROUNDS`` consecutive
       rounds — diminishing returns detected; rule engine exhausted.
    3. ``iterations >= max_iterations`` — safety cap reached.

    If the prompt already meets ``target_score`` before the first round,
    the function returns immediately with ``stopped_reason="already_optimal"``
    and an empty history.

    Args:
        prompt:          The starting prompt text.
        language:        Optional programming language key for language-specific
                         hints (dotnet, python, go, java, typescript; aliases
                         like c#, js, py are also accepted).
        context:         Optional background context injected once in round 1.
        target_score:    Score threshold (0-50) that signals "good enough".
                         Clamped to the valid range if out of bounds.
                         Default: 40.
        max_iterations:  Hard cap on the number of optimisation rounds.
                         Must be >= 1.  Default: 5.
        min_improvement: Minimum score gain per round before declaring
                         diminishing returns.  Default: 2.

    Returns:
        A dict with keys:
            final_prompt (str): The best prompt produced.
            initial_score (int): Score before any optimisation.
            final_score (int): Score after all rounds.
            total_improvement (int): ``final_score - initial_score``.
            iterations_used (int): Number of rounds that actually ran.
            max_iterations (int): The cap that was in effect.
            target_score (int): The target that was in effect.
            stopped_reason (str): One of the STOP_* constants above.
            history (list[dict]): Per-round data
                (round, prompt, score, improvement, changes, diff).

    Raises:
        TypeError:  If ``prompt`` is not a string.
        ValueError: If ``prompt`` is empty/whitespace, or ``max_iterations < 1``.
    """
    if not isinstance(prompt, str):
        raise TypeError(f"prompt must be a string, got {type(prompt).__name__!r}")
    if not prompt.strip():
        raise ValueError("prompt must not be empty or whitespace-only")
    if max_iterations < 1:
        raise ValueError(f"max_iterations must be >= 1, got {max_iterations!r}")

    # Clamp target_score to valid range
    target_score = max(_SCORE_MIN, min(_SCORE_MAX, target_score))

    # Evaluate starting state
    initial_analysis = analyze_prompt(prompt)
    initial_score: int = initial_analysis["total_score"]

    # Short-circuit: already meets the target
    if initial_score >= target_score:
        return LoopResult(
            final_prompt=prompt,
            initial_score=initial_score,
            final_score=initial_score,
            total_improvement=0,
            iterations_used=0,
            max_iterations=max_iterations,
            target_score=target_score,
            stopped_reason=STOP_ALREADY_OPTIMAL,
        ).to_dict()

    current_prompt = prompt
    current_score = initial_score
    history: list[LoopIteration] = []
    stall_count = 0
    stopped_reason = STOP_MAX_ITERATIONS

    for round_num in range(1, max_iterations + 1):
        # Only pass context in the first round to avoid duplication
        opt_result = optimize_prompt(
            prompt=current_prompt,
            language=language,
            context=context if round_num == 1 else None,
        )

        new_prompt: str = opt_result["optimized_prompt"]
        new_score: int = opt_result["score_after"]
        improvement = new_score - current_score

        # Guard: if optimization somehow worsened the score, keep the best version
        if new_score < current_score:
            new_prompt = current_prompt
            new_score = current_score
            improvement = 0

        diff = compute_prompt_diff(current_prompt, new_prompt)

        history.append(
            LoopIteration(
                round=round_num,
                prompt=new_prompt,
                score=new_score,
                improvement=improvement,
                changes=opt_result["changes_summary"],
                diff=diff,
            )
        )

        current_prompt = new_prompt
        current_score = new_score

        # Check termination conditions
        if current_score >= target_score:
            stopped_reason = STOP_TARGET_REACHED
            break

        if improvement < min_improvement:
            stall_count += 1
        else:
            stall_count = 0

        if stall_count >= _STALL_ROUNDS:
            stopped_reason = STOP_DIMINISHING_RETURNS
            break

    return LoopResult(
        final_prompt=current_prompt,
        initial_score=initial_score,
        final_score=current_score,
        total_improvement=current_score - initial_score,
        iterations_used=len(history),
        max_iterations=max_iterations,
        target_score=target_score,
        stopped_reason=stopped_reason,
        history=history,
    ).to_dict()
