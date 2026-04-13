"""Tests for the shared input validation helper."""

from __future__ import annotations

import pytest

from src.tools.validation import MAX_PROMPT_LENGTH, validate_prompt


class TestValidatePrompt:
    def test_valid_string_returns_stripped(self) -> None:
        assert validate_prompt("  hello  ") == "hello"

    def test_no_stripping_needed(self) -> None:
        assert validate_prompt("hello") == "hello"

    def test_type_error_on_int(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            validate_prompt(42)  # type: ignore[arg-type]

    def test_type_error_on_none(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            validate_prompt(None)  # type: ignore[arg-type]

    def test_type_error_on_list(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            validate_prompt(["a", "b"])  # type: ignore[arg-type]

    def test_value_error_on_empty_string(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            validate_prompt("")

    def test_value_error_on_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace"):
            validate_prompt("   \n\t  ")

    def test_value_error_on_exceeding_max_length(self) -> None:
        big = "x" * (MAX_PROMPT_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds the maximum"):
            validate_prompt(big)

    def test_exactly_max_length_is_accepted(self) -> None:
        ok = "x" * MAX_PROMPT_LENGTH
        assert validate_prompt(ok) == ok

    def test_custom_param_name_in_error(self) -> None:
        with pytest.raises(TypeError, match="objective"):
            validate_prompt(42, param_name="objective")  # type: ignore[arg-type]

    def test_custom_param_name_in_value_error(self) -> None:
        with pytest.raises(ValueError, match="objective"):
            validate_prompt("", param_name="objective")
