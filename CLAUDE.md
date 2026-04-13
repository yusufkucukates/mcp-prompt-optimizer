# CLAUDE.md — Project Instructions for Claude Code

This file is read automatically by Claude Code when working in this repository.
Follow all conventions here without asking for confirmation.

---

## Project Purpose

`prompt-optimizer-mcp` is a Python MCP (Model Context Protocol) server that scores,
rewrites, and iteratively optimizes AI prompts — deterministically, with zero API keys,
and zero external dependencies beyond the MCP SDK.

It solves a real pain point: agents and developers feed weak prompts to AI models and
get mediocre results. This server gives them a measurable, offline improvement pipeline.

---

## Tech Stack

| Component | Details |
|-----------|---------|
| Language | Python 3.11+ |
| MCP SDK | `mcp[cli]>=1.0.0` (low-level server API) |
| Transport | **stdio only** — no HTTP, no WebSocket |
| Build | Hatchling (`pyproject.toml`) |
| Tests | pytest + pytest-cov |
| Linting | ruff |
| Types | mypy --strict |

---

## Project Structure

```
src/
  server.py            MCP server entry point; registers tools and resources; stdio transport
  cli.py               Standalone CLI (prompt-optimizer); not an MCP server
  tools/
    analyze_prompt.py  Scores a prompt 0-50 across 5 quality dimensions (pure function)
    optimize_prompt.py Single-pass deterministic rewrite; returns diff + before/after scores
    optimize_loop.py   Iterative loop: runs rounds until target score or diminishing returns
    decompose_task.py  Breaks a task into subtasks for code/devops/generic agent types
    generate_code_prompt.py  Generates language-specific code generation prompts
    diff_utils.py      difflib wrapper; returns unified diff string between two prompts
  resources/
    template_manager.py  Loads .md templates from templates/ as MCP resources

templates/             Markdown prompt templates exposed as prompt-template:// URIs
tests/                 pytest unit tests; pure functions only, no MCP server dependency
.github/workflows/     CI (ruff, mypy, pytest on 3.11-3.13) + release to PyPI on tags
```

---

## How to Run Locally

```bash
# Install with dev dependencies
make install

# Start the MCP server (stdio transport — connect via Claude Code / Cursor)
make run

# Use the standalone CLI (no MCP client needed)
prompt-optimizer "write an api for users"
prompt-optimizer --loop "make an api" --language python --target-score 40
echo "fix the login bug" | prompt-optimizer --loop --json
```

---

## How to Run Tests

```bash
make test           # all tests with coverage
make test-fast      # skip slow tests (mark with @pytest.mark.slow)
make check          # lint + typecheck + test in one command
```

---

## Code Conventions

### Type Hints and Docstrings
- Every public function **must** have full type annotations (PEP 484)
- Use `from __future__ import annotations` at the top of every module
- Write Google-style docstrings for all public functions and classes
- `mypy --strict` must pass with zero errors — this is enforced in CI

### Tool Module Purity
- Tool modules in `src/tools/` are **pure functions** — they must never import from `src/server.py`
- No side effects: no disk writes, no network calls, no global state mutation
- Same input → same output, always. No randomness, no timestamps, no UUIDs

### Error Handling
- Tool functions raise `TypeError` for wrong-type inputs, `ValueError` for invalid values
- `src/server.py` catches all exceptions in `handle_call_tool` and returns them as MCP error JSON
- Never let an exception propagate to the MCP protocol layer unhandled

### Logging
- **Log to `sys.stderr` only** — `stdout` is the MCP stdio transport channel
- Never use `print()` in `src/` files except where explicitly writing to `sys.stderr`
- The pattern: `print("...", file=sys.stderr)`

### Imports
- Sorted by isort rules (ruff enforces this automatically)
- No circular imports: `tools/` ← `server.py` is fine; `server.py` ← `tools/` is not

---

## MCP-Specific Rules

### Transport
- The server uses **stdio transport exclusively** — `mcp.server.stdio.stdio_server()`
- Do NOT add HTTP endpoints, REST routes, or async web frameworks to `server.py`
- Do NOT add SSE or WebSocket handlers without creating a separate server module

### Tool Descriptions
- Tool descriptions in `TOOL_DEFINITIONS` are read by **LLMs**, not humans
- Write them as imperative action sentences that describe what the tool does and when to use it
- Include parameter names and acceptable values in the description
- Bad: "Optimizes a prompt" — Good: "Optimize a prompt by detecting vague instructions, injecting role definitions, and applying language-specific best practices. Returns the improved prompt, changes summary, and before/after quality scores."

### inputSchema
- Every tool schema **must** include a `"required": [...]` array
- Optional parameters must NOT appear in `"required"`
- Integer parameters (like `target_score`) must use `"type": "integer"`, not `"type": "number"`

### Resources
- Templates in `templates/*.md` are exposed as `prompt-template://{stem}` URIs
- New templates are picked up automatically — no code changes needed in `server.py`
- Template names use `snake_case`; no hyphens in filenames

---

## Common Pitfalls

1. **Printing to stdout crashes the MCP connection.** Any `print()` without `file=sys.stderr`
   will inject text into the stdio JSON-RPC stream and disconnect the client immediately.

2. **Importing `src.server` in a tool module creates a circular import** that silently makes
   some tool registrations fail. Tools must only import from `src.tools.*` and `src.resources.*`.

3. **The scoring scale is 0-50 (5 dimensions × 0-10 each).** If you add a new dimension you
   must update `DIMENSION_CHECKS`, `DIMENSION_SUGGESTIONS`, and every test that asserts on
   `total_score` bounds. The score cap in `_score_dimension` is per-dimension, not total.

4. **The `optimize_prompt_loop` tool passes `context` only in round 1.** If you move context
   injection to later rounds you will get duplicate `Context:` blocks in the output. The loop
   intentionally passes `context=None` for rounds 2+.

5. **`.vscode/settings.json` and `.vscode/launch.json` are gitignored** (personal configs).
   Only `.vscode/extensions.json` is committed. If you create personal launch configs,
   they stay local automatically — do not force-add them.

---

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new optimization rule for passive voice
fix: correct score clamping in analyze_prompt
chore: update pre-commit hooks
docs: improve CONTRIBUTING.md rule-contribution guide
test: add edge case tests for empty template URIs
ci: add Python 3.13 to test matrix
```

Scope is optional. Breaking changes get `!` after the type: `feat!: rename tool`.
