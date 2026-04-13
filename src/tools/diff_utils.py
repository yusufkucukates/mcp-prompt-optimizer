"""Utility for producing human-readable diffs between two prompt strings."""

from __future__ import annotations

import difflib

_MAX_DIFF_CHARS = 2000
_TRUNCATION_NOTICE = "\n... (diff truncated)"


def compute_prompt_diff(before: str, after: str) -> str:
    """Return a unified-diff-style string showing line-level changes.

    The output uses ``+`` for added lines and ``-`` for removed lines,
    with up to 3 lines of context around each change.  Identical inputs
    produce an empty string.  Very long diffs are truncated at
    ``_MAX_DIFF_CHARS`` characters with a notice appended.

    Args:
        before: The original prompt text.
        after:  The optimised prompt text.

    Returns:
        A human-readable diff string, or ``""`` if the texts are identical.
    """
    if before == after:
        return ""

    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile="before",
            tofile="after",
            lineterm="",
            n=3,
        )
    )

    if not diff_lines:
        return ""

    result = "\n".join(diff_lines)

    if len(result) > _MAX_DIFF_CHARS:
        result = result[:_MAX_DIFF_CHARS] + _TRUNCATION_NOTICE

    return result
