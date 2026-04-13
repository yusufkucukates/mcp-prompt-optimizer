"""Tests for all four tool modules.

Each tool module is tested as a pure function with no server or MCP dependency.
"""

from __future__ import annotations

import pytest

from src.tools.analyze_prompt import analyze_prompt
from src.tools.decompose_task import decompose_task
from src.tools.generate_code_prompt import generate_code_prompt
from src.tools.optimize_prompt import optimize_prompt  # async since v0.2.0

# ---------------------------------------------------------------------------
# Shared prompt fixtures
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# analyze_prompt tests
# ---------------------------------------------------------------------------

WELL_STRUCTURED_PROMPT = (
    "You are a senior Python engineer. "
    "Implement a REST API endpoint using FastAPI that accepts a JSON body "
    "containing a user_id (integer) and returns a JSON object with the user's "
    "profile data. Use async/await for the database call. "
    "Return HTTP 404 with a clear error message if the user does not exist. "
    "Follow PEP 8 and add type hints to all functions."
)

VAGUE_PROMPT = "do stuff"


class TestAnalyzePrompt:
    def test_returns_required_keys(self) -> None:
        result = analyze_prompt(WELL_STRUCTURED_PROMPT)
        assert "total_score" in result
        assert "score_normalized" in result
        assert "dimensions" in result
        assert "weak_spots" in result
        assert "suggestions" in result

    def test_score_normalized_is_0_to_100(self) -> None:
        result = analyze_prompt(WELL_STRUCTURED_PROMPT)
        assert 0 <= result["score_normalized"] <= 100

    def test_score_normalized_proportional_to_total(self) -> None:
        result = analyze_prompt(WELL_STRUCTURED_PROMPT)
        expected = round(result["total_score"] / 50 * 100)
        assert result["score_normalized"] == expected

    def test_dimensions_contain_all_five(self) -> None:
        result = analyze_prompt(WELL_STRUCTURED_PROMPT)
        expected = {"clarity", "specificity", "context", "output_definition", "actionability"}
        assert set(result["dimensions"].keys()) == expected

    def test_well_structured_prompt_scores_high(self) -> None:
        result = analyze_prompt(WELL_STRUCTURED_PROMPT)
        assert result["total_score"] >= 30, (
            f"Expected high score for well-structured prompt, got {result['total_score']}"
        )

    def test_vague_prompt_scores_low(self) -> None:
        result = analyze_prompt(VAGUE_PROMPT)
        assert result["total_score"] < 10, (
            f"Expected low score for vague prompt, got {result['total_score']}"
        )

    def test_type_error_on_non_string_input(self) -> None:
        with pytest.raises(TypeError, match="prompt must be a string"):
            analyze_prompt(12345)  # type: ignore[arg-type]

    def test_type_error_on_none_input(self) -> None:
        with pytest.raises(TypeError, match="prompt must be a string"):
            analyze_prompt(None)  # type: ignore[arg-type]

    def test_vague_prompt_has_weak_spots(self) -> None:
        result = analyze_prompt(VAGUE_PROMPT)
        assert len(result["weak_spots"]) > 0

    def test_weak_spots_have_suggestions(self) -> None:
        result = analyze_prompt(VAGUE_PROMPT)
        assert len(result["suggestions"]) == len(result["weak_spots"])

    def test_empty_prompt_returns_zero_score(self) -> None:
        result = analyze_prompt("")
        assert result["total_score"] == 0
        assert len(result["weak_spots"]) == 5

    def test_dimension_scores_are_bounded(self) -> None:
        result = analyze_prompt(WELL_STRUCTURED_PROMPT)
        for dim, score in result["dimensions"].items():
            assert 0 <= score <= 10, f"Dimension '{dim}' score {score} out of range"

    def test_total_score_equals_sum_of_dimensions(self) -> None:
        result = analyze_prompt(WELL_STRUCTURED_PROMPT)
        assert result["total_score"] == sum(result["dimensions"].values())


# ---------------------------------------------------------------------------
# optimize_prompt tests
# ---------------------------------------------------------------------------

class TestOptimizePrompt:
    async def test_returns_required_keys(self) -> None:
        result = await optimize_prompt("fix stuff")
        assert "optimized_prompt" in result
        assert "changes_summary" in result
        assert "score_before" in result
        assert "score_after" in result
        assert "score_normalized_before" in result
        assert "score_normalized_after" in result
        assert "engine_used" in result
        assert result["engine_used"] == "rules"

    async def test_improves_score_for_vague_prompt(self) -> None:
        result = await optimize_prompt(VAGUE_PROMPT)
        assert result["score_after"] >= result["score_before"], (
            f"score_after={result['score_after']} should be >= score_before={result['score_before']}"
        )

    async def test_changes_summary_is_non_empty(self) -> None:
        result = await optimize_prompt(VAGUE_PROMPT)
        assert isinstance(result["changes_summary"], list)
        assert len(result["changes_summary"]) > 0

    async def test_vague_words_are_replaced(self) -> None:
        result = await optimize_prompt("Please do something with the stuff in the repo.")
        prompt = result["optimized_prompt"].lower()
        assert "something" not in prompt or "a specific output" in prompt

    async def test_language_python_injects_hints(self) -> None:
        result = await optimize_prompt("write a data pipeline", language="python")
        prompt = result["optimized_prompt"].lower()
        assert any(
            term in prompt
            for term in ["type hints", "pep 8", "docstring", "pytest", "python"]
        )

    async def test_language_dotnet_injects_hints(self) -> None:
        result = await optimize_prompt("build an API", language="dotnet")
        prompt = result["optimized_prompt"].lower()
        assert any(
            term in prompt
            for term in ["async", "solid", "nullable", "dependency injection", "c#"]
        )

    async def test_context_appears_in_optimized_prompt(self) -> None:
        ctx = "We are migrating a legacy monolith to microservices."
        result = await optimize_prompt("refactor the user service", context=ctx)
        assert ctx in result["optimized_prompt"]

    async def test_role_is_prepended_when_absent(self) -> None:
        result = await optimize_prompt("List the top five sorting algorithms.")
        prompt = result["optimized_prompt"].lower()
        assert any(kw in prompt for kw in ["you are", "act as", "engineer", "expert"])

    async def test_score_before_matches_analyze_score(self) -> None:
        analysis = analyze_prompt(VAGUE_PROMPT)
        result = await optimize_prompt(VAGUE_PROMPT)
        assert result["score_before"] == analysis["total_score"]

    async def test_well_structured_prompt_has_no_breaking_changes(self) -> None:
        result = await optimize_prompt(WELL_STRUCTURED_PROMPT)
        assert "FastAPI" in result["optimized_prompt"]

    async def test_type_error_on_non_string_prompt(self) -> None:
        with pytest.raises(TypeError, match="prompt must be a string"):
            await optimize_prompt(42)  # type: ignore[arg-type]

    async def test_value_error_on_empty_prompt(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            await optimize_prompt("")

    async def test_value_error_on_whitespace_only_prompt(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            await optimize_prompt("   \n\t  ")

    async def test_language_alias_csharp_resolves_to_dotnet(self) -> None:
        result = await optimize_prompt("build an API", language="c#")
        prompt = result["optimized_prompt"].lower()
        assert any(term in prompt for term in ["async", "solid", "nullable", "c#", ".net"])

    async def test_language_alias_js_resolves_to_typescript(self) -> None:
        result = await optimize_prompt("build a frontend", language="js")
        prompt = result["optimized_prompt"].lower()
        assert any(term in prompt for term in ["typescript", "strict", "jest", "eslint"])


# ---------------------------------------------------------------------------
# decompose_task tests
# ---------------------------------------------------------------------------

COMPLEX_CODE_TASK = (
    "Implement a user authentication service with JWT tokens, "
    "refresh token rotation, and role-based access control using Python and FastAPI."
)


class TestDecomposeTask:
    def test_returns_required_keys(self) -> None:
        result = decompose_task(COMPLEX_CODE_TASK)
        assert "subtasks" in result
        assert "execution_order" in result
        assert "total_complexity" in result

    def test_code_agent_produces_five_subtasks(self) -> None:
        result = decompose_task(COMPLEX_CODE_TASK, agent_type="code_agent")
        assert len(result["subtasks"]) == 5

    def test_devops_agent_produces_five_subtasks(self) -> None:
        result = decompose_task("Deploy the application to Kubernetes", agent_type="devops_agent")
        assert len(result["subtasks"]) == 5

    def test_generic_agent_produces_four_subtasks(self) -> None:
        result = decompose_task("Analyse sales data", agent_type="generic")
        assert len(result["subtasks"]) == 4

    def test_unknown_agent_type_falls_back_to_generic(self) -> None:
        result = decompose_task("some task", agent_type="unknown_agent")
        assert len(result["subtasks"]) == 4

    def test_each_subtask_has_required_fields(self) -> None:
        result = decompose_task(COMPLEX_CODE_TASK, agent_type="code_agent")
        required = {"id", "title", "prompt", "dependencies", "estimated_complexity"}
        for subtask in result["subtasks"]:
            assert required.issubset(subtask.keys()), (
                f"Subtask missing keys: {required - subtask.keys()}"
            )

    def test_execution_order_matches_subtask_ids(self) -> None:
        result = decompose_task(COMPLEX_CODE_TASK, agent_type="code_agent")
        subtask_ids = {st["id"] for st in result["subtasks"]}
        for eid in result["execution_order"]:
            assert eid in subtask_ids

    def test_first_subtask_has_no_dependencies(self) -> None:
        result = decompose_task(COMPLEX_CODE_TASK, agent_type="code_agent")
        first = result["subtasks"][0]
        assert first["dependencies"] == []

    def test_subsequent_subtasks_depend_on_previous(self) -> None:
        result = decompose_task(COMPLEX_CODE_TASK, agent_type="code_agent")
        subtasks = result["subtasks"]
        for i in range(1, len(subtasks)):
            assert subtasks[i - 1]["id"] in subtasks[i]["dependencies"]

    def test_total_complexity_is_valid(self) -> None:
        result = decompose_task(COMPLEX_CODE_TASK, agent_type="code_agent")
        assert result["total_complexity"] in ("low", "medium", "high")

    def test_high_complexity_task_detected(self) -> None:
        result = decompose_task("Migrate the legacy monolith database to distributed microservices")
        assert result["total_complexity"] == "high"

    def test_task_text_appears_in_subtask_prompts(self) -> None:
        task = "Build a real-time chat feature"
        result = decompose_task(task, agent_type="code_agent")
        for subtask in result["subtasks"]:
            assert task in subtask["prompt"]

    def test_type_error_on_non_string_task(self) -> None:
        with pytest.raises(TypeError, match="task must be a string"):
            decompose_task(123)  # type: ignore[arg-type]

    def test_value_error_on_empty_task(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            decompose_task("")

    def test_value_error_on_whitespace_only_task(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            decompose_task("   ")


# ---------------------------------------------------------------------------
# generate_code_prompt tests
# ---------------------------------------------------------------------------

class TestGenerateCodePrompt:
    def test_returns_required_keys(self) -> None:
        result = generate_code_prompt("Build a REST API", "python")
        assert "prompt" in result
        assert "metadata" in result

    def test_metadata_contains_required_keys(self) -> None:
        result = generate_code_prompt("Build a REST API", "python")
        meta = result["metadata"]
        assert "language" in meta
        assert "framework" in meta
        assert "estimated_tokens" in meta

    def test_estimated_tokens_is_positive(self) -> None:
        result = generate_code_prompt("Build a REST API", "python")
        assert result["metadata"]["estimated_tokens"] > 0

    def test_objective_appears_in_prompt(self) -> None:
        objective = "Build a REST API for user management"
        result = generate_code_prompt(objective, "python")
        assert objective in result["prompt"]

    def test_python_prompt_contains_python_hints(self) -> None:
        result = generate_code_prompt("Write a data processor", "python")
        prompt = result["prompt"].lower()
        assert any(term in prompt for term in ["pep 8", "type hints", "pytest", "docstring"])

    def test_dotnet_prompt_contains_dotnet_hints(self) -> None:
        result = generate_code_prompt("Build a REST API", "dotnet")
        prompt = result["prompt"].lower()
        assert any(term in prompt for term in ["async/await", "solid", "nullable", "c#"])

    def test_go_prompt_contains_go_hints(self) -> None:
        result = generate_code_prompt("Build a CLI tool", "go")
        prompt = result["prompt"].lower()
        assert any(term in prompt for term in ["context.context", "goroutine", "interface", "go"])

    def test_java_prompt_contains_java_hints(self) -> None:
        result = generate_code_prompt("Build a service layer", "java")
        prompt = result["prompt"].lower()
        assert any(term in prompt for term in ["optional", "spring", "junit", "java"])

    def test_typescript_prompt_contains_ts_hints(self) -> None:
        result = generate_code_prompt("Build a frontend component", "typescript")
        prompt = result["prompt"].lower()
        assert any(term in prompt for term in ["strict", "typescript", "jest", "interface"])

    def test_framework_appears_in_prompt(self) -> None:
        result = generate_code_prompt("Build an API", "python", framework="FastAPI")
        assert "FastAPI" in result["prompt"]

    def test_custom_style_guide_overrides_default(self) -> None:
        custom_style = "Use tabs for indentation. Max line length: 120."
        result = generate_code_prompt("Build a CLI", "python", style_guide=custom_style)
        assert custom_style in result["prompt"]

    def test_tdd_instruction_is_present(self) -> None:
        result = generate_code_prompt("Build a calculator", "python")
        prompt = result["prompt"].lower()
        assert any(term in prompt for term in ["test", "tdd", "test-driven"])

    def test_unknown_language_falls_back_gracefully(self) -> None:
        result = generate_code_prompt("Build something", "cobol")
        assert result["prompt"]
        assert result["metadata"]["estimated_tokens"] > 0

    def test_language_alias_csharp_resolves_correctly(self) -> None:
        result_alias = generate_code_prompt("Build an API", "c#")
        result_canon = generate_code_prompt("Build an API", "dotnet")
        assert result_alias["metadata"]["language"] == result_canon["metadata"]["language"]

    def test_language_alias_py_resolves_to_python(self) -> None:
        result = generate_code_prompt("Write a script", "py")
        assert result["metadata"]["language"] == "Python"

    def test_language_alias_js_resolves_to_typescript(self) -> None:
        result = generate_code_prompt("Build a component", "js")
        assert result["metadata"]["language"] == "TypeScript"

    def test_language_alias_golang_resolves_to_go(self) -> None:
        result = generate_code_prompt("Write a server", "golang")
        assert result["metadata"]["language"] == "Go"

    def test_type_error_on_non_string_objective(self) -> None:
        with pytest.raises(TypeError, match="objective must be a string"):
            generate_code_prompt(42, "python")  # type: ignore[arg-type]

    def test_type_error_on_non_string_language(self) -> None:
        with pytest.raises(TypeError, match="language must be a string"):
            generate_code_prompt("build something", 99)  # type: ignore[arg-type]

    def test_value_error_on_empty_objective(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            generate_code_prompt("", "python")

    def test_value_error_on_whitespace_only_objective(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            generate_code_prompt("   ", "python")
