"""Meta-tool: optimize a task prompt, decompose it, and generate code prompts per subtask."""

from __future__ import annotations

from typing import Any

from src.llm.base import LLMProvider
from src.tools.decompose_task import decompose_task
from src.tools.generate_code_prompt import generate_code_prompt
from src.tools.optimize_prompt import optimize_prompt
from src.tools.validation import validate_prompt


async def optimize_and_run(
    task: str,
    language: str = "python",
    agent_type: str = "code_agent",
    context: str | None = None,
    provider: LLMProvider | None = None,
    llm_threshold: int = 80,
) -> dict[str, Any]:
    """Optimize a task prompt, decompose it into subtasks, and generate code prompts.

    This meta-tool chains three tools in a single call:

    1. ``optimize_prompt`` — improves the raw task description.
    2. ``decompose_task`` — breaks the optimized task into ordered subtasks.
    3. ``generate_code_prompt`` — generates a production-ready code prompt for
       each subtask using the specified language.

    The result contains everything an agentic coding loop needs to begin
    execution immediately — no further processing required.

    Args:
        task: The raw task description to optimize and execute.
        language: Target programming language (default: ``"python"``).
        agent_type: Execution agent type passed to ``decompose_task``
                    (``"code_agent"``, ``"devops_agent"``, or ``"generic"``).
        context: Optional background context for the optimization step.
        provider: Optional :class:`LLMProvider` for hybrid optimization.
        llm_threshold: Normalized score threshold for LLM trigger (default: 80).

    Returns:
        A dict with keys:
            optimized_task (str): The improved task prompt.
            optimization_stats (dict): score_before, score_after, engine_used, changes_summary.
            decomposition (dict): Full result from decompose_task.
            subtask_prompts (list[dict]): Each entry has subtask_id, title, and code_prompt.
            language (str): Language used for code prompt generation.
            agent_type (str): Agent type used for decomposition.

    Raises:
        TypeError: If ``task`` is not a string.
        ValueError: If ``task`` is empty, whitespace-only, or too long.
    """
    validate_prompt(task, param_name="task")

    # Step 1 — Optimize the task prompt
    opt_result = await optimize_prompt(
        prompt=task,
        context=context,
        language=language,
        provider=provider,
        llm_threshold=llm_threshold,
    )
    optimized_task: str = opt_result["optimized_prompt"]

    # Step 2 — Decompose the optimized task
    decomp_result = decompose_task(task=optimized_task, agent_type=agent_type)

    # Step 3 — Generate a code prompt for each subtask
    subtask_prompts: list[dict[str, Any]] = []
    for subtask in decomp_result["subtasks"]:
        code_result = generate_code_prompt(
            objective=subtask["prompt"],
            language=language,
        )
        subtask_prompts.append(
            {
                "subtask_id": subtask["id"],
                "title": subtask["title"],
                "dependencies": subtask["dependencies"],
                "estimated_complexity": subtask["estimated_complexity"],
                "code_prompt": code_result["prompt"],
                "usage_hint": (
                    f"Execute this prompt with a {language} code agent. "
                    f"Dependencies: {subtask['dependencies'] or 'none'}."
                ),
            }
        )

    return {
        "optimized_task": optimized_task,
        "optimization_stats": {
            "score_before": opt_result["score_before"],
            "score_after": opt_result["score_after"],
            "score_normalized_before": opt_result["score_normalized_before"],
            "score_normalized_after": opt_result["score_normalized_after"],
            "engine_used": opt_result["engine_used"],
            "changes_summary": opt_result["changes_summary"],
        },
        "decomposition": decomp_result,
        "subtask_prompts": subtask_prompts,
        "language": language,
        "agent_type": agent_type,
        "usage_hint": (
            "Execute subtask_prompts in the order defined by "
            "decomposition.execution_order. Each subtask is self-contained."
        ),
    }
