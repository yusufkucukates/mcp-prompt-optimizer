"""Code-specific prompt generator for production-ready code generation tasks."""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Language configuration registry
# ---------------------------------------------------------------------------

LANGUAGE_CONFIG: dict[str, dict[str, str | list[str]]] = {
    "dotnet": {
        "display_name": "C# / .NET",
        "role_prefix": (
            "You are a senior C# / .NET engineer with deep expertise in ASP.NET Core, "
            "Entity Framework Core, and enterprise application architecture."
        ),
        "best_practices": [
            "Use async/await for all I/O-bound operations; never call .Result or .Wait().",
            "Enable nullable reference types (#nullable enable) and annotate all parameters.",
            "Apply SOLID principles throughout: prefer interfaces and dependency injection.",
            "Use record types for immutable DTOs; IReadOnlyList<T> for collection return types.",
            "Validate all inputs using FluentValidation or DataAnnotations before processing.",
            "Use ILogger<T> for structured logging; never Console.WriteLine in production code.",
        ],
        "test_framework": "xUnit + Moq",
        "style_notes": (
            "Follow Microsoft's C# coding conventions. Use PascalCase for public members, "
            "camelCase for local variables and parameters. Prefix interfaces with 'I'."
        ),
        "output_format": (
            "Provide the solution as one or more C# files. Include the namespace declaration, "
            "all necessary using directives, and XML documentation comments on public members."
        ),
    },
    "python": {
        "display_name": "Python",
        "role_prefix": (
            "You are a senior Python engineer with expertise in clean architecture, "
            "type-safe design, and Pythonic idioms."
        ),
        "best_practices": [
            "Add full type hints to every function signature (PEP 484); use from __future__ import annotations.",
            "Write Google-style docstrings for all public functions, classes, and modules.",
            "Follow PEP 8: snake_case for functions and variables, PascalCase for classes.",
            "Use dataclasses or Pydantic models for structured data; avoid plain dicts.",
            "Prefer pathlib.Path over os.path for filesystem operations.",
            "Handle exceptions explicitly; avoid bare except clauses.",
        ],
        "test_framework": "pytest",
        "style_notes": (
            "Follow PEP 8 and PEP 257. Maximum line length: 88 characters (Black formatter). "
            "Use double quotes for strings."
        ),
        "output_format": (
            "Provide the implementation as one or more Python files with module-level docstrings. "
            "Include a corresponding test file using pytest."
        ),
    },
    "go": {
        "display_name": "Go",
        "role_prefix": (
            "You are a senior Go engineer with expertise in concurrent systems, "
            "idiomatic Go design, and cloud-native services."
        ),
        "best_practices": [
            "Return errors as the last return value; handle every error — never use underscore for errors.",
            "Accept context.Context as the first parameter for any function doing I/O or long work.",
            "Define behaviour through interfaces; keep interfaces small (1-3 methods).",
            "Protect shared mutable state with sync.Mutex or communicate via channels.",
            "Use table-driven tests in *_test.go files.",
            "Follow the standard project layout: cmd/, internal/, pkg/.",
        ],
        "test_framework": "go test + testify",
        "style_notes": (
            "Run gofmt and golint before submitting. Use golangci-lint for static analysis. "
            "Package names should be lowercase, no underscores."
        ),
        "output_format": (
            "Provide the implementation as one or more .go files with package declaration "
            "and all necessary imports. Include a *_test.go file with table-driven tests."
        ),
    },
    "java": {
        "display_name": "Java",
        "role_prefix": (
            "You are a senior Java engineer with expertise in Spring Boot, "
            "Clean Architecture, and domain-driven design."
        ),
        "best_practices": [
            "Use Optional<T> instead of returning null; annotate parameters with @NonNull / @Nullable.",
            "Apply constructor injection with Spring's @Autowired (or implicit via Lombok @RequiredArgsConstructor).",
            "Use records (Java 16+) or Lombok @Value for immutable value objects.",
            "Mark transaction boundaries with @Transactional at the service layer.",
            "Write JUnit 5 tests with Mockito for mocking; use @SpringBootTest only for integration tests.",
            "Follow Clean Architecture: separate domain, application, and infrastructure packages.",
        ],
        "test_framework": "JUnit 5 + Mockito",
        "style_notes": (
            "Follow Google Java Style Guide. PascalCase for classes, camelCase for methods and variables. "
            "Use Checkstyle or Spotless for formatting enforcement."
        ),
        "output_format": (
            "Provide the implementation as Java source files with proper package declarations "
            "and Javadoc comments on public APIs. Include a corresponding test class."
        ),
    },
    "typescript": {
        "display_name": "TypeScript",
        "role_prefix": (
            "You are a senior TypeScript engineer with expertise in type-safe architecture, "
            "React ecosystems, and Node.js backend services."
        ),
        "best_practices": [
            "Enable strict mode in tsconfig.json; never use 'any' — prefer 'unknown' for untyped values.",
            "Define interfaces or types for all data shapes; use discriminated unions for variants.",
            "Handle errors with typed Result<T, E> patterns or custom error classes; avoid untyped catch.",
            "Use ESLint with @typescript-eslint/recommended; enforce import ordering with import/order.",
            "Write tests with Jest; mock external modules with jest.mock() and typed mocks.",
            "Use Zod or io-ts for runtime validation of external data (API responses, env vars).",
        ],
        "test_framework": "Jest + ts-jest",
        "style_notes": (
            "Follow the project's Prettier / ESLint configuration. Use const by default; "
            "avoid var. Prefer arrow functions for callbacks."
        ),
        "output_format": (
            "Provide the implementation as TypeScript source files with explicit type annotations. "
            "Include a corresponding *.test.ts or *.spec.ts file using Jest."
        ),
    },
}

FALLBACK_LANGUAGE_KEY = "python"

# ---------------------------------------------------------------------------
# Language alias normalisation map
# Maps common aliases → canonical LANGUAGE_CONFIG key
# ---------------------------------------------------------------------------

_LANGUAGE_ALIASES: dict[str, str] = {
    # Python
    "py": "python",
    "python3": "python",
    # TypeScript / JavaScript
    "ts": "typescript",
    "js": "typescript",
    "javascript": "typescript",
    "node": "typescript",
    "nodejs": "typescript",
    "node.js": "typescript",
    # C# / .NET
    "c#": "dotnet",
    "csharp": "dotnet",
    ".net": "dotnet",
    "net": "dotnet",
    # Go
    "golang": "go",
    # Java / Kotlin (mapped to Java config)
    "kt": "java",
    "kotlin": "java",
}

# ---------------------------------------------------------------------------
# Section separators and headers
# ---------------------------------------------------------------------------

_SECTION_SEP = "\n\n"


def _estimate_tokens(text: str) -> int:
    """Estimate token count using a word-based heuristic.

    Uses a factor of 1.3 words-per-token as a rough approximation.
    """
    word_count = len(text.split())
    return math.ceil(word_count * 1.3)


def generate_code_prompt(
    objective: str,
    language: str,
    framework: str | None = None,
    style_guide: str | None = None,
) -> dict:
    """Generate a production-ready prompt for a code generation task.

    The prompt includes: role definition, objective, framework context,
    style guidelines, language best practices, output format requirements,
    and a TDD instruction.

    Args:
        objective: What the code should accomplish.
        language: Target programming language key (dotnet, python, go, java, typescript).
                  Common aliases are accepted: py, js, ts, c#, csharp, golang, etc.
        framework: Optional framework or library (e.g. 'FastAPI', 'ASP.NET Core').
        style_guide: Optional custom style instructions; overrides language defaults.

    Returns:
        A dict with keys:
            prompt (str): The generated code generation prompt.
            metadata (dict): language, framework, estimated_tokens.

    Raises:
        TypeError: If ``objective`` or ``language`` is not a string.
        ValueError: If ``objective`` is empty or whitespace-only.
    """
    if not isinstance(objective, str):
        raise TypeError(f"objective must be a string, got {type(objective).__name__!r}")
    if not isinstance(language, str):
        raise TypeError(f"language must be a string, got {type(language).__name__!r}")
    if not objective.strip():
        raise ValueError("objective must not be empty or whitespace-only")

    raw_key = language.lower().strip()
    # Resolve aliases first, then look up the config; fall back to python if unknown
    lang_key = _LANGUAGE_ALIASES.get(raw_key, raw_key)
    config = LANGUAGE_CONFIG.get(lang_key, LANGUAGE_CONFIG[FALLBACK_LANGUAGE_KEY])

    sections: list[str] = []

    # 1 — Role definition
    role = config["role_prefix"]
    if framework:
        role = f"{role} You have extensive experience with {framework}."
    sections.append(role)

    # 2 — Objective
    sections.append(f"## Objective\n{objective.strip()}")

    # 3 — Framework context
    if framework:
        sections.append(
            f"## Framework / Library\nUse **{framework}** as the primary framework or library for this task. "
            f"Follow its conventions and recommended patterns."
        )

    # 4 — Style guide
    if style_guide and style_guide.strip():
        sections.append(f"## Style Guide\n{style_guide.strip()}")
    else:
        sections.append(f"## Style Guide\n{config['style_notes']}")

    # 5 — Constraints / best practices
    practices_text = "\n".join(f"- {p}" for p in config["best_practices"])
    sections.append(f"## Constraints and Best Practices\n{practices_text}")

    # 6 — Output format
    sections.append(f"## Output Format\n{config['output_format']}")

    # 7 — TDD instruction
    test_framework = config["test_framework"]
    sections.append(
        f"## Test-Driven Development\n"
        f"Write tests using **{test_framework}** first, then implement the code to make them pass. "
        f"Ensure all tests pass before considering the implementation complete. "
        f"Include both positive (happy-path) and negative (error/edge-case) test scenarios."
    )

    prompt = _SECTION_SEP.join(sections)

    return {
        "prompt": prompt,
        "metadata": {
            "language": config["display_name"],
            "framework": framework or "",
            "estimated_tokens": _estimate_tokens(prompt),
        },
    }
