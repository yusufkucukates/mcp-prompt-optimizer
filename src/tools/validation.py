"""Shared input validation helpers for all tool functions."""

from __future__ import annotations

MAX_PROMPT_LENGTH = 50_000


def validate_prompt(value: object, param_name: str = "prompt") -> str:
    """Validate that ``value`` is a non-empty string within the allowed length.

    Args:
        value: The input value to validate.
        param_name: Name of the parameter (used in error messages).

    Returns:
        The stripped string.

    Raises:
        TypeError:  If ``value`` is not a string.
        ValueError: If ``value`` is empty, whitespace-only, or exceeds
                    :const:`MAX_PROMPT_LENGTH` characters.
    """
    if not isinstance(value, str):
        raise TypeError(
            f"{param_name} must be a string, got {type(value).__name__!r}"
        )
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{param_name} must not be empty or whitespace-only")
    if len(stripped) > MAX_PROMPT_LENGTH:
        raise ValueError(
            f"{param_name} exceeds the maximum allowed length of "
            f"{MAX_PROMPT_LENGTH:,} characters (got {len(stripped):,})"
        )
    return stripped
