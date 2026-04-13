"""Core prompt optimization logic: vague-word replacement, structure injection,
and language-specific best-practice enrichment."""

from __future__ import annotations

import re

from src.tools.analyze_prompt import analyze_prompt
from src.tools.diff_utils import compute_prompt_diff
from src.tools.generate_code_prompt import _LANGUAGE_ALIASES

# ---------------------------------------------------------------------------
# Vague-word replacement rules: (regex_pattern, replacement, description)
# ---------------------------------------------------------------------------

VAGUE_WORD_RULES: list[tuple[str, str, str]] = [
    (r"\bsomething\b", "a specific output", "Replaced 'something' with 'a specific output'"),
    (r"\bstuff\b", "components", "Replaced 'stuff' with 'components'"),
    (r"\bthings\b", "elements", "Replaced 'things' with 'elements'"),
    (r"\bsomehow\b", "by following the steps below", "Replaced 'somehow' with actionable directive"),
    (r"\bmaybe\b", "optionally", "Replaced 'maybe' with 'optionally'"),
    (r"\bperhaps\b", "optionally", "Replaced 'perhaps' with 'optionally'"),
    (r"\bkind of\b", "", "Removed filler phrase 'kind of'"),
    (r"\bsort of\b", "", "Removed filler phrase 'sort of'"),
    (r"\ba bit\b", "", "Removed filler phrase 'a bit'"),
    (r"\bsomewhat\b", "", "Removed filler phrase 'somewhat'"),
    (r"\betc\.?\b", "(list all relevant items explicitly)", "Replaced 'etc.' with explicit instruction"),
    (r"\band so on\b", "(enumerate all relevant items)", "Replaced 'and so on' with explicit instruction"),
    (r"\bwhatever\b", "the appropriate option", "Replaced 'whatever' with 'the appropriate option'"),
]

# ---------------------------------------------------------------------------
# Language-specific best-practice injections
# ---------------------------------------------------------------------------

LANGUAGE_HINTS: dict[str, dict[str, str | list[str]]] = {
    "dotnet": {
        "label": "C# / .NET",
        "practices": [
            "Use async/await for all I/O-bound operations; avoid .Result or .Wait() to prevent deadlocks.",
            "Enable nullable reference types (#nullable enable) and annotate all parameters.",
            "Follow SOLID principles: single responsibility, open/closed, Liskov substitution, "
            "interface segregation, dependency inversion.",
            "Register services via dependency injection (IServiceCollection); avoid service locator.",
            "Use record types for immutable DTOs; prefer IReadOnlyList<T> over List<T> for return types.",
        ],
    },
    "python": {
        "label": "Python",
        "practices": [
            "Add full type hints to all function signatures (PEP 484); use from __future__ import annotations.",
            "Write Google-style or NumPy-style docstrings for all public functions and classes.",
            "Follow PEP 8 style guidelines: snake_case for functions/variables, PascalCase for classes.",
            "Use dataclasses or Pydantic models instead of plain dicts for structured data.",
            "Write pytest unit tests; use fixtures for shared setup and parametrize for multiple inputs.",
        ],
    },
    "go": {
        "label": "Go",
        "practices": [
            "Return errors as the last return value; never ignore them.",
            "Use context.Context as the first parameter for all functions doing I/O or long operations.",
            "Prefer interfaces over concrete types for function parameters to improve testability.",
            "Protect shared state with sync.Mutex or use channels; avoid data races.",
            "Follow the standard Go project layout (cmd/, internal/, pkg/).",
        ],
    },
    "java": {
        "label": "Java",
        "practices": [
            "Use Optional<T> instead of returning null; annotate with @NonNull / @Nullable.",
            "Apply Spring best practices: constructor injection over field injection, @Transactional boundaries.",
            "Prefer immutable value objects; use records (Java 16+) or Lombok @Value.",
            "Write JUnit 5 tests with Mockito for dependency mocking; aim for high branch coverage.",
            "Follow Clean Architecture: separate domain, application, and infrastructure layers.",
        ],
    },
    "typescript": {
        "label": "TypeScript",
        "practices": [
            "Enable strict mode in tsconfig.json; avoid any; prefer unknown for untyped values.",
            "Define interfaces or types for all data shapes; use discriminated unions for variants.",
            "Handle errors with typed Result<T, E> or custom error classes; avoid untyped catch blocks.",
            "Write tests with Jest and @testing-library where appropriate; mock external modules.",
            "Use ESLint with @typescript-eslint/recommended; enforce consistent import ordering.",
        ],
    },
}

# ---------------------------------------------------------------------------
# Role definitions injected when none are present
# ---------------------------------------------------------------------------

GENERIC_ROLE_PREFIX = (
    "You are an expert assistant with deep knowledge in software engineering "
    "and best practices."
)

LANGUAGE_ROLE_PREFIX: dict[str, str] = {
    "dotnet": "You are a senior C# / .NET engineer with expertise in enterprise application architecture.",
    "python": "You are a senior Python engineer with expertise in clean code, testing, and Pythonic design.",
    "go": "You are a senior Go engineer with expertise in concurrent systems and idiomatic Go patterns.",
    "java": "You are a senior Java engineer with expertise in Spring Boot, Clean Architecture, and DDD.",
    "typescript": "You are a senior TypeScript engineer with expertise in type-safe frontend and Node.js systems.",
}

# ---------------------------------------------------------------------------
# Output format templates appended when none is detected
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_INSTRUCTION = (
    "\n\nPlease format your response with clear sections. "
    "Use markdown headings for each section and include code examples where relevant."
)

# ---------------------------------------------------------------------------
# Constraint section appended to very short prompts
# ---------------------------------------------------------------------------

DEFAULT_CONSTRAINT_SECTION = (
    "\n\nConstraints:\n"
    "- Keep the solution concise and focused on the stated objective.\n"
    "- Do not introduce unnecessary dependencies.\n"
    "- Handle edge cases and error conditions explicitly."
)

# Pattern to detect existing role statements
_ROLE_PATTERN = re.compile(r"\b(you are|act as|assume the role|as a|as an)\b", re.IGNORECASE)

# Pattern to detect existing output format mentions
_OUTPUT_PATTERN = re.compile(
    r"\b(json|xml|yaml|markdown|table|list|code block|plain text|format as|return a|output a)\b",
    re.IGNORECASE,
)

# Pattern to detect existing constraint mentions
_CONSTRAINT_PATTERN = re.compile(
    r"\b(must not|do not|avoid|constraint|requirement|restriction|limit|maximum|minimum)\b",
    re.IGNORECASE,
)


def optimize_prompt(
    prompt: str,
    context: str | None = None,
    language: str | None = None,
) -> dict:
    """Optimize a prompt by applying deterministic improvement rules.

    Steps applied in order:
    1. Score the original prompt.
    2. Replace vague words with specific alternatives.
    3. Prepend a role definition if none exists.
    4. Inject context section if ``context`` is provided.
    5. Append language-specific best practices if ``language`` is provided.
    6. Append output format instruction if none detected.
    7. Append constraint section for very short prompts without constraints.
    8. Re-score the optimized prompt.

    Args:
        prompt: The original prompt text.
        context: Optional background context to inject.
        language: Optional programming language key (dotnet, python, go, java, typescript).

    Returns:
        A dict with keys:
            optimized_prompt (str): The improved prompt.
            changes_summary (list[str]): Human-readable list of changes made.
            score_before (int): Total quality score before optimization.
            score_after (int): Total quality score after optimization.

    Raises:
        TypeError: If ``prompt`` is not a string.
        ValueError: If ``prompt`` is empty or whitespace-only.
    """
    if not isinstance(prompt, str):
        raise TypeError(f"prompt must be a string, got {type(prompt).__name__!r}")
    if not prompt.strip():
        raise ValueError("prompt must not be empty or whitespace-only")
    original = prompt.strip()
    analysis_before = analyze_prompt(original)
    score_before: int = analysis_before["total_score"]

    working = original
    changes: list[str] = []

    # Step 1 — Vague word replacement
    for pattern, replacement, description in VAGUE_WORD_RULES:
        new_working, count = re.subn(pattern, replacement, working, flags=re.IGNORECASE)
        if count > 0:
            working = new_working.strip()
            changes.append(description)

    # Step 2 — Role injection
    if not _ROLE_PATTERN.search(working):
        raw_lang = (language or "").lower().strip()
        lang_key = _LANGUAGE_ALIASES.get(raw_lang, raw_lang)
        role = LANGUAGE_ROLE_PREFIX.get(lang_key, GENERIC_ROLE_PREFIX)
        working = f"{role}\n\n{working}"
        changes.append("Prepended role definition to establish agent persona")

    # Step 3 — Context injection
    if context and context.strip():
        context_block = f"\n\nContext:\n{context.strip()}"
        working = working + context_block
        changes.append("Injected provided context as a dedicated 'Context:' section")

    # Step 4 — Language-specific best practices
    raw_lang4 = (language or "").lower().strip()
    lang_key = _LANGUAGE_ALIASES.get(raw_lang4, raw_lang4)
    if lang_key and lang_key in LANGUAGE_HINTS:
        lang_info = LANGUAGE_HINTS[lang_key]
        practices_block = (
            f"\n\n{lang_info['label']} Best Practices to Follow:\n"
            + "\n".join(f"- {p}" for p in lang_info["practices"])
        )
        working = working + practices_block
        changes.append(f"Injected {lang_info['label']}-specific best practices")

    # Step 5 — Output format
    if not _OUTPUT_PATTERN.search(working):
        working = working + DEFAULT_OUTPUT_INSTRUCTION
        changes.append("Appended output format guidance (no format was specified)")

    # Step 6 — Constraint section for short prompts
    word_count = len(working.split())
    if word_count < 80 and not _CONSTRAINT_PATTERN.search(working):
        working = working + DEFAULT_CONSTRAINT_SECTION
        changes.append("Appended default constraint section (prompt was concise with no constraints)")

    if not changes:
        changes.append("No changes needed — prompt was already well-structured")

    analysis_after = analyze_prompt(working)
    score_after: int = analysis_after["total_score"]

    return {
        "optimized_prompt": working,
        "changes_summary": changes,
        "score_before": score_before,
        "score_after": score_after,
        "diff": compute_prompt_diff(original, working),
    }
