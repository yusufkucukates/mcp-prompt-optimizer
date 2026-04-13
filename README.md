# prompt-optimizer-mcp

[![CI](https://github.com/yusufkucukates/mcp-prompt-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/yusufkucukates/mcp-prompt-optimizer/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/prompt-optimizer-mcp.svg)](https://pypi.org/project/prompt-optimizer-mcp/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-139%20passed-brightgreen.svg)](tests/)

**Stop feeding weak prompts to AI. This MCP server scores, rewrites, and iteratively optimizes your prompts — instantly, offline, zero API keys.**

The only MCP server that shows you *exactly* how your prompt improved at every step, with measurable before/after scores and a line-by-line diff.

---

## Demo

> *Recording coming soon — see the [Before/After](#beforeafter) section for a live example.*

```
$ prompt-optimizer --loop "make an api for users" --language python

Loop Optimization
  Initial score : 5/50

  Round 1  5/50  →  26/50  (+21 pts)
    • Prepended role definition to establish agent persona
    • Replaced 'make' → 'implement'
    • Appended output format guidance

  Round 2  26/50  →  38/50  (+12 pts)
    • Injected Python-specific best practices (PEP 8, type hints, pytest)
    • Appended default constraint section

  Round 3  38/50  →  42/50  (+4 pts)
    • Added TDD instruction

  Final: 5/50  →  42/50  (+37 pts in 3 rounds)
  Stopped: target score reached

Optimized Prompt:
  You are a senior Python engineer with expertise in clean architecture,
  type-safe design, and Pythonic idioms.

  Implement a specific output for users.
  ...
```

---

## Why This Exists

Every other prompt optimization tool requires an **LLM API key**, a vector database, or complex setup. This one needs none of that.

| | prompt-optimizer-mcp | Competitors |
|--|--|--|
| **Setup** | `pip install` | API key + config |
| **Speed** | Instant (pure Python) | LLM round-trip latency |
| **Cost** | Free, forever | Per-call API cost |
| **Offline** | Yes | No |
| **Before/after score** | Yes, every round | No |
| **Iterative loop** | Built-in, self-terminating | No |
| **Language-aware** | 5 languages + aliases | No |

---

## Install

```bash
pip install prompt-optimizer-mcp
```

Or install from source:

```bash
git clone https://github.com/yusufkucukates/mcp-prompt-optimizer.git
cd mcp-prompt-optimizer
pip install -e ".[dev]"
```

---

## Connect to Your AI Client

<details>
<summary><strong>Claude Code</strong></summary>

Add to your `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "prompt-optimizer": {
      "command": "prompt-optimizer-mcp"
    }
  }
}
```
</details>

<details>
<summary><strong>Cursor</strong></summary>

In Cursor settings → MCP → Add server:

```json
{
  "prompt-optimizer": {
    "command": "prompt-optimizer-mcp",
    "args": []
  }
}
```

Or add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "prompt-optimizer": {
      "command": "prompt-optimizer-mcp"
    }
  }
}
```
</details>

<details>
<summary><strong>Claude Desktop</strong></summary>

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "prompt-optimizer": {
      "command": "prompt-optimizer-mcp"
    }
  }
}
```
</details>

<details>
<summary><strong>Any MCP client (manual stdio)</strong></summary>

```bash
prompt-optimizer-mcp
```

The server communicates over stdio. Point any MCP client at this command.
</details>

---

## Before/After

### Input (7 words, score: 5/50)

```
make an api for users
```

### Output after `optimize_prompt_loop` (score: 42/50, +37 points)

```
You are a senior Python engineer with expertise in clean architecture,
type-safe design, and Pythonic idioms.

## Objective
Implement a specific output for users.

## Constraints and Best Practices
- Add full type hints to every function signature (PEP 484)
- Write Google-style docstrings for all public functions
- Follow PEP 8: snake_case for functions, PascalCase for classes
- Use dataclasses or Pydantic models for structured data
- Handle exceptions explicitly; avoid bare except clauses

## Output Format
Provide the implementation as one or more Python files with module-level
docstrings. Include a corresponding test file using pytest.

## Test-Driven Development
Write tests using pytest first, then implement the code to make them pass.
```

**Changes made (visible in diff output):**
```diff
-make an api for users
+You are a senior Python engineer with expertise in clean architecture,
+type-safe design, and Pythonic idioms.
+
+## Objective
+Implement a specific output for users.
...
```

---

## Tools

### 1. `optimize_prompt` — 1-Click Optimization

Single-pass deterministic rewrite. Instant.

| Input | Type | Required |
|-------|------|----------|
| `prompt` | string | Yes |
| `language` | string | No — `python`, `dotnet`, `go`, `java`, `typescript` (+ aliases: `py`, `c#`, `js`, `ts`, `golang`) |
| `context` | string | No |

**Returns:** `optimized_prompt`, `changes_summary`, `score_before`, `score_after`, `diff`

---

### 2. `optimize_prompt_loop` — Agentic Iterative Loop

Runs multiple rounds, stops when good enough. Use this in pipelines.

| Input | Type | Default |
|-------|------|---------|
| `prompt` | string | required |
| `language` | string | — |
| `context` | string | — |
| `target_score` | integer | 40 |
| `max_iterations` | integer | 5 |
| `min_improvement` | integer | 2 |

**Stop conditions (first one wins):**
1. `score >= target_score` — quality goal achieved
2. `improvement < min_improvement` for 2 consecutive rounds — diminishing returns
3. `iterations >= max_iterations` — safety cap

**Returns:** `final_prompt`, `initial_score`, `final_score`, `total_improvement`, `iterations_used`, `stopped_reason`, `history[]` (per-round: `score`, `improvement`, `changes`, `diff`)

---

### 3. `analyze_prompt` — Quality Scorer

Scores a prompt across 5 dimensions (0-10 each, total 0-50).

| Input | Type | Required |
|-------|------|----------|
| `prompt` | string | Yes |

**Returns:** `total_score`, `dimensions` (clarity, specificity, context, output_definition, actionability), `weak_spots`, `suggestions`

---

### 4. `decompose_task` — Agentic Subtask Breakdown

Breaks a complex task into sequential, dependency-tracked subtasks.

| Input | Type | Default |
|-------|------|---------|
| `task` | string | required |
| `agent_type` | string | `generic` — also: `code_agent`, `devops_agent` |

**Returns:** `subtasks[]`, `execution_order`, `total_complexity`

---

### 5. `generate_code_prompt` — Language-Specific Code Prompt

Generates a production-ready code generation prompt with role, best practices, style guide, and TDD instructions.

| Input | Type | Required |
|-------|------|----------|
| `objective` | string | Yes |
| `language` | string | Yes |
| `framework` | string | No |
| `style_guide` | string | No |

**Returns:** `prompt`, `metadata` (language, framework, estimated_tokens)

---

## Prompt Templates (MCP Resources)

Exposed as MCP resources — your AI client can read them directly.

| URI | Description |
|-----|-------------|
| `prompt-template://agentic_task_decomposition` | Chain-of-thought task decomposition meta-prompt |
| `prompt-template://code_generation` | Universal code generation template |
| `prompt-template://debug_analysis` | Hypothesis-first debugging template |
| `prompt-template://dotnet_code_review` | Structured C# / .NET code review |

---

## CLI Usage

Works without any MCP client — just `pip install` and run.

```bash
# 1-click optimization
prompt-optimizer "write an api for user management"

# Iterative loop
prompt-optimizer --loop "write an api" --target-score 40

# Language-aware
prompt-optimizer "build a REST API" --language python

# Show analysis before optimizing
prompt-optimizer --analyze "my prompt" --loop

# JSON output for CI/pipelines
prompt-optimizer --loop "my prompt" --json

# Pipe mode
echo "fix the user login bug" | prompt-optimizer --loop --json
```

---

## Development

```bash
make install-dev  # pip install -e ".[dev]"
make test         # pytest with coverage
make lint         # ruff check
make typecheck    # mypy --strict
make run          # start the MCP server
```

**Architecture:** Pure functions in `src/tools/` (no side effects, fully testable). Thin MCP adapter in `src/server.py`. All optimization is deterministic — same input always produces the same output.

**Test suite:** 139 tests across tools, loop engine, diff utility, template manager, and CLI.

---

## Roadmap

### v0.1.0 (current)
- [x] `analyze_prompt` — 5-dimension quality scorer
- [x] `optimize_prompt` — 1-click deterministic rewrite with diff
- [x] `optimize_prompt_loop` — agentic iterative loop with 3 stop conditions
- [x] `decompose_task` — subtask breakdown for code/devops/generic agents
- [x] `generate_code_prompt` — language-specific code generation prompts
- [x] Standalone CLI (`prompt-optimizer`)
- [x] 4 MCP resource templates
- [x] Language alias normalization (`c#`, `js`, `py`, `golang`, ...)
- [x] Input validation (TypeError, ValueError) across all tools
- [x] CI pipeline (ruff, mypy, pytest on Python 3.11/3.12/3.13)
- [x] 139 unit tests

### v1.0.0 (weeks 3-6)
- [ ] HTTP/SSE transport for webhook and pipeline integration
- [ ] MCP `prompts` capability (templates as first-class prompts)
- [ ] GitHub Actions action: `uses: prompt-optimizer-mcp/action@v1`
- [ ] 95%+ test coverage with server integration tests
- [ ] Auto-release to PyPI on git tag
- [ ] Terminal recording GIF for README

### v1.1.0 (weeks 7-12)
- [ ] YAML custom rule system — add your own optimization rules
- [ ] Community rule packs via `rules/` directory
- [ ] Prompt versioning to disk (save/load sessions)
- [ ] Domain-specific scoring profiles (code vs. writing prompts)

---

## Contributing

We welcome optimization rules, new templates, new language configs, and bug fixes.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

**Good first issues:**
- Add a vague-word replacement rule in `src/tools/optimize_prompt.py`
- Improve a scoring dimension pattern in `src/tools/analyze_prompt.py`
- Add a new Markdown prompt template in `templates/`

---

## License

MIT — see [LICENSE](LICENSE).
