# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- HTTP/SSE transport option for webhook and pipeline integration
- MCP `prompts` capability (expose templates as first-class MCP prompts)
- YAML custom rule system for community-contributed optimization rules
- Prompt history and versioning to disk
- Codecov badge integration
- GitHub Actions auto-release to PyPI on tag push

---

## [0.1.0] - 2026-04-13

### Added
- **`analyze_prompt` tool**: Scores a prompt 0-50 across five quality dimensions
  (clarity, specificity, context, output_definition, actionability) with per-dimension
  feedback and concrete improvement suggestions.
- **`optimize_prompt` tool**: Single-pass deterministic rewrite pipeline — vague-word
  replacement, role injection, context block injection, language-specific best practices,
  output format appendix, and constraint section. Returns before/after scores and a
  unified diff showing every change made.
- **`optimize_prompt_loop` tool** *(killer feature)*: Iterative agentic loop that runs
  multiple rounds of optimization and stops when any of three conditions is met:
  target score reached, diminishing returns detected, or iteration cap hit. Returns
  the complete per-round history with scores, diffs, and change summaries.
- **`decompose_task` tool**: Breaks a complex task into sequential, dependency-tracked
  subtasks for `code_agent`, `devops_agent`, or `generic` agent types.
- **`generate_code_prompt` tool**: Generates a production-ready, language-specific code
  generation prompt with role, objective, best practices, style guide, output format,
  and TDD instructions.
- **4 MCP resource templates** exposed via `prompt-template://` URIs:
  `agentic_task_decomposition`, `code_generation`, `debug_analysis`, `dotnet_code_review`.
- **Standalone CLI** (`prompt-optimizer`): One-click and loop modes with `--language`,
  `--context`, `--target-score`, `--max-iterations`, `--analyze`, and `--json` flags.
  Supports pipe mode (`echo "prompt" | prompt-optimizer`).
- **Language alias normalization**: Accepts `c#`, `csharp`, `py`, `js`, `ts`, `golang`,
  `kotlin` and maps them to the canonical language config keys.
- **Input validation**: `TypeError` for wrong-type inputs, `ValueError` for empty/whitespace
  strings, across all tool functions and the MCP server dispatch layer.
- **Before/after diff** in `optimize_prompt` and every loop iteration history entry.
- **Count-based scoring engine**: `_score_dimension` uses `re.findall` with per-pattern
  occurrence caps (max 3) so rich, detailed prompts reach higher scores.
- **CI pipeline** (GitHub Actions): ruff lint, mypy strict, pytest with coverage on
  Python 3.11, 3.12, and 3.13.
- **139 unit tests** covering all tools, the loop engine, diff utility, template manager,
  and CLI.

### Security
- Path traversal guard in `TemplateManager.get_template` — names that resolve outside
  the templates directory raise `ValueError`.
- Empty URI name guard in `template_uri_to_name` — `prompt-template://` with no name
  raises `ValueError`.

[Unreleased]: https://github.com/yusufkucukates/mcp-prompt-optimizer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yusufkucukates/mcp-prompt-optimizer/releases/tag/v0.1.0
