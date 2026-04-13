"""Agentic task decomposition: breaks a complex task into sequential, atomic subtasks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Complexity estimation keyword sets
# ---------------------------------------------------------------------------

HIGH_COMPLEXITY_KEYWORDS: frozenset[str] = frozenset(
    ["integrate", "migration", "migrate", "refactor", "redesign", "architect",
     "distributed", "concurrent", "security", "authentication", "authorization",
     "pipeline", "orchestrate", "kubernetes", "terraform", "infrastructure"]
)

MEDIUM_COMPLEXITY_KEYWORDS: frozenset[str] = frozenset(
    ["create", "implement", "build", "develop", "add", "extend", "update",
     "configure", "deploy", "automate", "generate", "optimize", "improve"]
)

LOW_COMPLEXITY_KEYWORDS: frozenset[str] = frozenset(
    ["fix", "rename", "move", "delete", "remove", "format", "lint",
     "document", "comment", "log", "print", "copy", "list", "read"]
)

# ---------------------------------------------------------------------------
# Agent-type phase templates
# Each phase: (id_suffix, title_template, prompt_template)
# {task} is replaced with the user's task description
# ---------------------------------------------------------------------------

AGENT_PHASES: dict[str, list[dict[str, str]]] = {
    "code_agent": [
        {
            "id_suffix": "plan",
            "title": "Plan and design the solution",
            "prompt_template": (
                "Analyze the following task and produce a detailed implementation plan.\n"
                "Identify the components to create or modify, data structures, interfaces, "
                "and the overall approach.\n\nTask: {task}\n\n"
                "Output: A structured plan listing files, classes, functions, and their responsibilities."
            ),
        },
        {
            "id_suffix": "implement",
            "title": "Implement the core logic",
            "prompt_template": (
                "Implement the solution as planned in the previous step.\n"
                "Write clean, production-ready code for the following task.\n\n"
                "Task: {task}\n\n"
                "Requirements:\n"
                "- Follow the design from the planning phase.\n"
                "- Handle all error cases and edge conditions.\n"
                "- Add inline documentation for non-obvious logic.\n\n"
                "Output: Complete, working source code files."
            ),
        },
        {
            "id_suffix": "test",
            "title": "Write tests",
            "prompt_template": (
                "Write comprehensive tests for the implementation of the following task.\n\n"
                "Task: {task}\n\n"
                "Requirements:\n"
                "- Cover happy paths, edge cases, and error scenarios.\n"
                "- Use appropriate mocking for external dependencies.\n"
                "- Aim for high branch coverage.\n\n"
                "Output: Test files with descriptive test names and assertions."
            ),
        },
        {
            "id_suffix": "review",
            "title": "Review and refine",
            "prompt_template": (
                "Review the implementation and tests for the following task.\n\n"
                "Task: {task}\n\n"
                "Review checklist:\n"
                "- Code correctness and logic errors.\n"
                "- Performance bottlenecks or unnecessary allocations.\n"
                "- Security concerns (input validation, secrets, injection).\n"
                "- Adherence to SOLID / clean code principles.\n\n"
                "Output: Annotated list of issues found and suggested fixes."
            ),
        },
        {
            "id_suffix": "document",
            "title": "Write documentation",
            "prompt_template": (
                "Write documentation for the completed implementation of the following task.\n\n"
                "Task: {task}\n\n"
                "Include:\n"
                "- Module/function-level docstrings or XML docs.\n"
                "- README section explaining usage and configuration.\n"
                "- Example snippets showing typical usage.\n\n"
                "Output: Documentation in the appropriate format for the project's language."
            ),
        },
    ],
    "devops_agent": [
        {
            "id_suffix": "assess",
            "title": "Assess current infrastructure and requirements",
            "prompt_template": (
                "Assess the current infrastructure state and define requirements for the following task.\n\n"
                "Task: {task}\n\n"
                "Identify: existing resources, dependencies, access requirements, and risk areas.\n\n"
                "Output: Assessment report with current state and gap analysis."
            ),
        },
        {
            "id_suffix": "configure",
            "title": "Configure and prepare resources",
            "prompt_template": (
                "Configure all infrastructure resources and tools required for the following task.\n\n"
                "Task: {task}\n\n"
                "Requirements:\n"
                "- Follow infrastructure-as-code best practices.\n"
                "- Use environment variables / secrets management for credentials.\n"
                "- Ensure idempotent configuration.\n\n"
                "Output: Configuration files (IaC, YAML manifests, Dockerfile, etc.)."
            ),
        },
        {
            "id_suffix": "deploy",
            "title": "Execute deployment",
            "prompt_template": (
                "Execute the deployment for the following task using the prepared configuration.\n\n"
                "Task: {task}\n\n"
                "Requirements:\n"
                "- Use rolling or blue-green deployment strategy to minimise downtime.\n"
                "- Log all deployment steps with timestamps.\n"
                "- Implement rollback capability.\n\n"
                "Output: Deployment execution log and confirmation of success."
            ),
        },
        {
            "id_suffix": "verify",
            "title": "Verify deployment health",
            "prompt_template": (
                "Verify that the deployment for the following task is healthy and functional.\n\n"
                "Task: {task}\n\n"
                "Verification steps:\n"
                "- Run smoke tests against the deployed service.\n"
                "- Check health endpoints and resource metrics.\n"
                "- Confirm rollback readiness if issues are detected.\n\n"
                "Output: Verification report with pass/fail status for each check."
            ),
        },
        {
            "id_suffix": "monitor",
            "title": "Set up monitoring and alerts",
            "prompt_template": (
                "Configure monitoring, logging, and alerting for the deployed resources from the following task.\n\n"
                "Task: {task}\n\n"
                "Requirements:\n"
                "- Define meaningful alert thresholds (latency, error rate, resource utilisation).\n"
                "- Configure log aggregation and retention policies.\n"
                "- Document runbook steps for each alert.\n\n"
                "Output: Monitoring configuration and alert runbook."
            ),
        },
    ],
    "generic": [
        {
            "id_suffix": "analyze",
            "title": "Analyze and understand the task",
            "prompt_template": (
                "Analyze the following task thoroughly before taking any action.\n\n"
                "Task: {task}\n\n"
                "Identify: the core objective, constraints, unknowns, and success criteria.\n\n"
                "Output: A brief analysis summary with identified inputs, outputs, and risks."
            ),
        },
        {
            "id_suffix": "plan",
            "title": "Create an execution plan",
            "prompt_template": (
                "Based on the analysis, create a step-by-step execution plan for the following task.\n\n"
                "Task: {task}\n\n"
                "The plan should list discrete, actionable steps in execution order with clear deliverables.\n\n"
                "Output: Numbered execution plan with dependencies noted."
            ),
        },
        {
            "id_suffix": "execute",
            "title": "Execute the plan",
            "prompt_template": (
                "Execute each step of the plan for the following task.\n\n"
                "Task: {task}\n\n"
                "Requirements:\n"
                "- Complete each step fully before moving to the next.\n"
                "- Record any deviations from the plan.\n"
                "- Handle errors and blockers explicitly.\n\n"
                "Output: Completed deliverables for each execution step."
            ),
        },
        {
            "id_suffix": "validate",
            "title": "Validate results",
            "prompt_template": (
                "Validate the results of the completed task against the original requirements.\n\n"
                "Task: {task}\n\n"
                "Validation checklist:\n"
                "- Does the output meet all stated requirements?\n"
                "- Are edge cases handled?\n"
                "- Is the result ready to hand off or deploy?\n\n"
                "Output: Validation report with pass/fail for each success criterion."
            ),
        },
    ],
}

COMPLEXITY_LEVELS: tuple[str, ...] = ("low", "medium", "high")

COMPLEXITY_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


@dataclass
class Subtask:
    """A single atomic subtask within a decomposed workflow."""

    id: str
    title: str
    prompt: str
    dependencies: list[str] = field(default_factory=list)
    estimated_complexity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict."""
        return {
            "id": self.id,
            "title": self.title,
            "prompt": self.prompt,
            "dependencies": self.dependencies,
            "estimated_complexity": self.estimated_complexity,
        }


def _estimate_complexity(task: str) -> str:
    """Estimate task complexity based on keyword density.

    Returns 'low', 'medium', or 'high'.
    """
    words = set(re.findall(r"\b\w+\b", task.lower()))

    if words & HIGH_COMPLEXITY_KEYWORDS:
        return "high"
    if words & MEDIUM_COMPLEXITY_KEYWORDS:
        return "medium"
    return "low"


def _topological_order(subtasks: list[Subtask]) -> list[str]:
    """Return subtask IDs in topological (execution) order.

    Because dependencies are always the immediately preceding subtask,
    this is equivalent to the original list order, but we compute it
    properly for correctness.
    """
    id_set = {st.id for st in subtasks}
    visited: list[str] = []
    visiting: set[str] = set()
    id_map: dict[str, Subtask] = {st.id: st for st in subtasks}

    def visit(st_id: str) -> None:
        if st_id in visiting:
            return  # cycle guard
        if st_id in visited:
            return
        visiting.add(st_id)
        for dep in id_map[st_id].dependencies:
            if dep in id_set:
                visit(dep)
        visiting.discard(st_id)
        visited.append(st_id)

    for st in subtasks:
        visit(st.id)

    return visited


def decompose_task(task: str, agent_type: str = "generic") -> dict[str, Any]:
    """Break a complex task into sequential, atomic subtasks.

    Args:
        task: Natural-language description of the task to decompose.
        agent_type: One of 'code_agent', 'devops_agent', or 'generic'.
                    Defaults to 'generic' for unknown values.

    Returns:
        A dict with keys:
            subtasks (list[dict]): Ordered list of subtask objects.
            execution_order (list[str]): Subtask IDs in dependency order.
            total_complexity (str): Aggregate complexity (low/medium/high).

    Raises:
        TypeError: If ``task`` is not a string.
        ValueError: If ``task`` is empty or whitespace-only.
    """
    if not isinstance(task, str):
        raise TypeError(f"task must be a string, got {type(task).__name__!r}")
    if not task.strip():
        raise ValueError("task must not be empty or whitespace-only")
    agent_key = agent_type.lower().strip()
    if agent_key not in AGENT_PHASES:
        agent_key = "generic"

    phases = AGENT_PHASES[agent_key]
    task_complexity = _estimate_complexity(task)

    subtasks: list[Subtask] = []
    for index, phase in enumerate(phases):
        subtask_id = f"subtask-{index + 1}-{phase['id_suffix']}"
        prompt = phase["prompt_template"].format(task=task)
        deps = [subtasks[-1].id] if subtasks else []

        subtasks.append(
            Subtask(
                id=subtask_id,
                title=phase["title"],
                prompt=prompt,
                dependencies=deps,
                estimated_complexity=task_complexity,
            )
        )

    # Overall complexity is the highest seen (all phases inherit task complexity,
    # but we compute properly so future phase-specific complexity works too)
    max_level = max(
        (COMPLEXITY_ORDER[st.estimated_complexity] for st in subtasks),
        default=0,
    )
    total_complexity = COMPLEXITY_LEVELS[max_level]
    execution_order = _topological_order(subtasks)

    return {
        "subtasks": [st.to_dict() for st in subtasks],
        "execution_order": execution_order,
        "total_complexity": total_complexity,
    }
