# Contributing to prompt-optimizer-mcp

Thank you for helping make prompts better for everyone.

This document covers everything you need to contribute — from fixing a typo
to adding a new optimization rule or a full new tool.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Ways to Contribute](#ways-to-contribute)
3. [Adding a New Optimization Rule](#adding-a-new-optimization-rule)
4. [Adding a New Prompt Template](#adding-a-new-prompt-template)
5. [Development Workflow](#development-workflow)
6. [Code Standards](#code-standards)
7. [Issue Labels](#issue-labels)
8. [Pull Request Checklist](#pull-request-checklist)

---

## Quick Start

```bash
# Fork and clone
git clone https://github.com/<your-username>/mcp-prompt-optimizer.git
cd mcp-prompt-optimizer

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
make test

# Run the CLI to verify your setup
prompt-optimizer "write an api" --loop --json
```

---

## Ways to Contribute

| Type | Effort | Impact | Label |
|------|--------|--------|-------|
| Fix a typo / improve docs | Tiny | Medium | `good first issue` |
| Add a new vague-word replacement rule | Small | High | `good first issue` |
| Improve a scoring dimension pattern | Small | High | `enhancement` |
| Add a new markdown prompt template | Small | Medium | `good first issue` |
| Add a new language config (e.g. Rust, Swift) | Medium | High | `enhancement` |
| Add a new optimization rule category | Medium | High | `enhancement` |
| Fix a bug | Varies | High | `bug` |
| Add a new MCP tool | Large | High | `feature` |

---

## Adding a New Optimization Rule

The simplest contribution with the highest impact. Optimization rules live in
`src/tools/optimize_prompt.py` as entries in `VAGUE_WORD_RULES`.

Each rule is a 3-tuple: `(regex_pattern, replacement, description)`.

**Example — adding a rule for "obviously":**

```python
# In VAGUE_WORD_RULES
(r"\bobviously\b", "", "Removed filler word 'obviously'"),
```

**Rules for good optimization rules:**
- Target hedges, filler words, and vague nouns (`stuff`, `things`, `somehow`)
- Replacements must be more specific than the original
- The description must be a past-tense human-readable sentence
- Add a test in `tests/test_tools.py::TestOptimizePrompt`

**Improving scoring patterns** (`src/tools/analyze_prompt.py`):

Each `DIMENSION_CHECKS` entry is a `(regex_pattern, weight)` tuple.  
Patterns use `re.findall` with per-pattern occurrence caps.  
Open a PR with before/after scores for a representative set of prompts.

---

## Adding a New Prompt Template

Templates are Markdown files in `templates/` and are automatically exposed
as MCP resources at `prompt-template://<filename_without_md>`.

1. Create `templates/your_template_name.md`
2. Write a well-structured Markdown prompt (use existing templates as reference)
3. The template is immediately available — no code changes needed
4. Add it to the Templates table in `README.md`

**Naming convention:** `snake_case`, descriptive, no hyphens.

---

## Development Workflow

```bash
# Create a feature branch
git checkout -b feat/your-feature-name

# Make changes

# Run the full quality pipeline before committing
make lint       # ruff check
make typecheck  # mypy --strict
make test       # pytest with coverage

# Or run everything at once
make all
```

**Pre-commit hooks** (optional but recommended):

```bash
pip install pre-commit
pre-commit install
```

This runs ruff and trailing-whitespace checks automatically on every commit.

---

## Code Standards

- **Type hints**: All public functions must have full type annotations. `mypy --strict` must pass.
- **Docstrings**: Google-style for all public functions and classes.
- **Tests**: Every new feature needs tests. Aim for 90%+ coverage.
- **No new runtime dependencies**: The core package has exactly one dependency (`mcp[cli]`). Keep it that way. Dev tools go in `[dev]` extras only.
- **No LLM calls**: All optimization logic is deterministic, offline, and free. This is a core design principle.
- **Line length**: 100 characters (enforced by ruff).
- **Imports**: Sorted by isort rules (ruff enforces this).

---

## Issue Labels

| Label | Meaning |
|-------|---------|
| `good first issue` | Straightforward change, ideal for first-time contributors |
| `bug` | Something is broken |
| `enhancement` | Improving existing functionality |
| `feature` | New capability |
| `documentation` | Docs-only change |
| `optimization-rule` | New or improved prompt optimization rule |
| `template` | New or improved prompt template |
| `help wanted` | Maintainer needs community help |

---

## Pull Request Checklist

Before submitting a PR, confirm:

- [ ] `make lint` passes (zero ruff errors)
- [ ] `make typecheck` passes (zero mypy errors)
- [ ] `make test` passes (all existing tests green, new tests added for new code)
- [ ] `CHANGELOG.md` updated under `[Unreleased]` with a description of the change
- [ ] PR description explains *what* changed and *why*
- [ ] For new optimization rules: before/after example included in the PR description

---

## Questions?

Open a [GitHub Discussion](https://github.com/yusufkucukates/mcp-prompt-optimizer/discussions)
or file an issue. We respond quickly.
