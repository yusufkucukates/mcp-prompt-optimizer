"""Prompt quality analyzer that scores prompts across 5 dimensions."""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Scoring dimension definitions
# Each entry maps to a list of (regex_pattern, weight) tuples.
# Weights sum to the maximum score (10) per dimension.
# ---------------------------------------------------------------------------

DIMENSION_CHECKS: dict[str, list[tuple[str, int]]] = {
    # Each list entry: (regex_pattern, weight_per_occurrence).
    # _score_dimension counts occurrences (capped at 3 per pattern), multiplies by
    # weight, then caps the dimension total at 10.  All weights are calibrated so
    # that a rich, detailed prompt can reach the full 10.
    "clarity": [
        (r"\b(specifically|precisely|exactly|clearly|clear|explicitly)\b", 2),
        (r"\b(must|should|shall|need to|required to|ensure)\b", 2),
        # Multi-sentence structure (two consecutive sentence-ending punctuation spans)
        (r"[.!?][^.!?]+[.!?]", 2),
        (r"\b(use|follow|apply|add|do not|avoid|include|exclude)\b", 2),
        # Numbered / sequential structure
        (r"\b(numbered|step[s]?|in order|sequential|one by one)\b", 2),
    ],
    "specificity": [
        (r"\b\d+\b", 2),                                  # numeric constraints
        (r"\b(JSON|XML|YAML|CSV|markdown|HTML|table|list|array|dict)\b", 2),
        (r"\b(function|class|method|module|endpoint|API|database|schema)\b", 2),
        (r"\b(less than|more than|at most|at least|between|maximum|minimum|integer|string|boolean)\b", 2),
        # Named identifiers / typed fields suggest concrete specification
        (r"\b(named|called|typed|field|property|parameter|argument|attribute)\b", 2),
    ],
    "context": [
        (r"\b(you are|act as|assume|given that|in the context of|as a)\b", 3),
        (r"\b(because|since|therefore|the reason|background|scenario)\b", 2),
        (r"\b(project|codebase|application|system|service|platform)\b", 2),
        (r"\b(existing|current|legacy|production|our)\b", 1),
        # Persona depth keywords reward explicit role / seniority framing
        (r"\b(senior|expert|specialist|experienced|professional|engineer|architect)\b", 2),
    ],
    "output_definition": [
        (r"\b(returns?|output|produce|generate|respond with|format as|structure as)\b", 2),
        (r"\b(JSON|XML|YAML|markdown|plain text|code block|table|bullet|numbered|object|array)\b", 2),
        (r"\b(example|sample|like this|following format|template)\b", 2),
        (r"\b(include|exclude|omit|without|with the following)\b", 2),
        # HTTP status codes in the output spec signal well-defined error handling
        (r"\b(HTTP [1-5]\d{2}|4\d{2}|5\d{2}|2\d{2})\b", 2),
    ],
    "actionability": [
        (r"^(create|write|implement|build|develop|design|analyze|review|fix|generate|refactor|add|update|remove|use|follow)\b",
         3),
        (r"\b(create|write|implement|build|develop|design|analyze|review|fix|generate|refactor|use|follow|apply)\b", 2),
        (r"\b(step[s]?|phase|first|then|finally|lastly|next)\b", 2),
        (r"\b(by|using|via|with|through|based on)\b", 1),
        # Numbered list items ("1." / "1)" / "(1)") reward explicit step structure
        (r"\b\d+[.)]\s|\(\d+\)", 2),
    ],
}

AMBIGUITY_PENALTIES: list[str] = [
    r"\b(maybe|perhaps|somehow|something|stuff|things|whatever|etc\.?|and so on)\b",
    r"\b(kind of|sort of|a bit|somewhat)\b",
]

DIMENSION_SUGGESTIONS: dict[str, str] = {
    "clarity": (
        "Clarify your intent by using precise, unambiguous language. "
        "Replace vague hedges (maybe, somehow, stuff) with specific directives. "
        "Use imperative sentences: 'Implement X so that Y.'"
    ),
    "specificity": (
        "Add concrete constraints: specify counts, sizes, formats, or named "
        "technologies. For example: 'Return a JSON array of at most 10 items' "
        "instead of 'return some results'."
    ),
    "context": (
        "Provide role and background context. Start with 'You are a senior X engineer "
        "working on Y'. Describe the existing system, language, or framework in use."
    ),
    "output_definition": (
        "Define the expected output format explicitly. Specify whether you want JSON, "
        "markdown, a code block, or a table. Include an example or schema if possible."
    ),
    "actionability": (
        "Start with a strong imperative verb (Create, Implement, Analyze, Write). "
        "Break multi-step tasks into numbered steps so an agent can act immediately."
    ),
}


def _score_dimension(text: str, dimension: str) -> int:
    """Score a single dimension for the given prompt text.

    Uses count-based scoring: each pattern can contribute up to 3 occurrences
    multiplied by its weight.  The total is capped at 10 per dimension.  This rewards
    depth (multiple constraints, several numbered steps, repeated role cues)
    rather than binary presence.

    Returns a value between 0 and 10.
    """
    checks = DIMENSION_CHECKS[dimension]
    raw_score = 0

    for pattern, weight in checks:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        # Cap each pattern at 3 occurrences to prevent a single pattern from
        # dominating the score when the prompt is repetitive rather than rich.
        raw_score += min(len(matches), 3) * weight

    # Apply ambiguity penalty to clarity only
    if dimension == "clarity":
        penalty = 0
        for pattern in AMBIGUITY_PENALTIES:
            matches = re.findall(pattern, text, re.IGNORECASE)
            penalty += len(matches)
        raw_score = max(0, raw_score - penalty)

    # Cap at 10
    return min(10, raw_score)


def analyze_prompt(prompt: str) -> dict[str, Any]:
    """Analyze a prompt and score it across 5 quality dimensions.

    Each dimension is scored 0-10. Weak dimensions (score < 5) are flagged
    as weak spots with concrete improvement suggestions.

    Args:
        prompt: The prompt text to analyze.

    Returns:
        A dict with keys:
            total_score (int): Sum of all dimension scores (0-50).
            dimensions (dict): Score per dimension.
            weak_spots (list[str]): Dimension names scoring below 5.
            suggestions (list[str]): Improvement advice for each weak spot.

    Raises:
        TypeError: If ``prompt`` is not a string.
    """
    if not isinstance(prompt, str):
        raise TypeError(f"prompt must be a string, got {type(prompt).__name__!r}")
    if not prompt or not prompt.strip():
        return {
            "total_score": 0,
            "dimensions": {dim: 0 for dim in DIMENSION_CHECKS},
            "weak_spots": list(DIMENSION_CHECKS.keys()),
            "suggestions": list(DIMENSION_SUGGESTIONS.values()),
        }

    text = prompt.strip()
    dimensions: dict[str, int] = {}

    for dimension in DIMENSION_CHECKS:
        dimensions[dimension] = _score_dimension(text, dimension)

    total_score = sum(dimensions.values())
    weak_spots = [dim for dim, score in dimensions.items() if score < 5]
    suggestions = [DIMENSION_SUGGESTIONS[dim] for dim in weak_spots]

    return {
        "total_score": total_score,
        "dimensions": dimensions,
        "weak_spots": weak_spots,
        "suggestions": suggestions,
    }
