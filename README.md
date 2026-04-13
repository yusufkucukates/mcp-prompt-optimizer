# mcp-prompt-optimizer

[![CI](https://github.com/yusufkucukates/mcp-prompt-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/yusufkucukates/mcp-prompt-optimizer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/prompt-optimizer-mcp)](https://pypi.org/project/prompt-optimizer-mcp/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Works with Claude Code](https://img.shields.io/badge/Claude_Code-compatible-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)

**The MCP server that turns vague AI prompts into production-ready instructions — works offline, gets smarter with an API key.**

Stop writing the same boilerplate prompt engineering by hand. This MCP server runs inside Claude Code, Cursor, and any MCP-compatible client. It scores, improves, and decomposes your prompts before they reach any model — so every AI call starts from a higher baseline.

---

## Before → After (real output)

| | Prompt | Score |
|---|---|---|
| **Before** | `write some code to handle users` | **10 / 100** |
| **After (rules)** | Role injected · vague words replaced · format defined · constraints added | **60 / 100** |
| **After (hybrid)** | LLM refines weak dimensions on top of rule output | **85+ / 100** |

```
# Before
write some code to handle users

# After (rules engine, no API key needed)
You are an expert assistant with deep knowledge in software engineering and best practices.

Write code to handle users with a specific output.

Python Best Practices to Follow:
- Add full type hints to all function signatures (PEP 484)
- Write Google-style docstrings for all public functions
- Follow PEP 8: snake_case for functions, PascalCase for classes
- Use dataclasses or Pydantic models for structured data
- Write pytest unit tests; use fixtures for shared setup

Please format your response with clear sections.
Use markdown headings for each section and include code examples where relevant.

Constraints:
- Keep the solution concise and focused on the stated objective.
- Do not introduce unnecessary dependencies.
- Handle edge cases and error conditions explicitly.
```

---

## Quick Install

```bash
# Install from PyPI
pip install prompt-optimizer-mcp

# Or clone and install locally
git clone https://github.com/yusufkucukates/mcp-prompt-optimizer
cd mcp-prompt-optimizer
pip install -e .

# With Anthropic LLM enhancement
pip install -e ".[anthropic]"

# With OpenAI LLM enhancement
pip install -e ".[openai]"
```

---

## MCP Client Configuration

### Claude Code (`~/.claude.json`)

```json
{
  "mcpServers": {
    "prompt-optimizer": {
      "command": "prompt-optimizer-mcp",
      "env": {
        "PROMPT_OPTIMIZER_LLM": "true",
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "PROMPT_OPTIMIZER_THRESHOLD": "70"
      }
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "prompt-optimizer": {
      "command": "prompt-optimizer-mcp",
      "env": {
        "PROMPT_OPTIMIZER_LLM": "false"
      }
    }
  }
}
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PROMPT_OPTIMIZER_LLM` | `false` | Enable LLM enhancement layer |
| `PROMPT_OPTIMIZER_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `PROMPT_OPTIMIZER_API_KEY` | — | API key (falls back to `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) |
| `PROMPT_OPTIMIZER_MODEL` | `claude-haiku-4-*` | Override model name |
| `PROMPT_OPTIMIZER_THRESHOLD` | `80` | Normalized score (0-100) below which LLM is triggered |

---

## Architecture: Hybrid Engine

```
Input Prompt
     │
     ▼
Layer 1: Rule Engine (always runs, zero latency, no API key)
  • Vague word replacement
  • Role injection
  • Language-specific best practices
  • Output format enforcement
  • Constraint section
     │
     ▼
score_normalized >= threshold? ──Yes──► Return result (engine_used: "rules")
     │ No
     ▼
Layer 2: LLM Enhancement (optional, requires API key)
  • Focused improvement on weak dimensions only
  • Minimal, purposeful changes
  • Falls back to rule output on any error
     │
     ▼
Return result (engine_used: "hybrid")
```

---

## Tool Reference

### `optimize_prompt`
Improve a single prompt. Returns optimized text, score comparison, line-by-line diff, and engine used.

```json
{
  "prompt": "write some code to handle users",
  "language": "python",
  "context": "This is a FastAPI service on AWS Lambda."
}
```

**Returns:** `optimized_prompt`, `score_before`, `score_after`, `score_normalized_before`, `score_normalized_after`, `engine_used`, `diff`, `changes_summary`

---

### `analyze_prompt`
Score a prompt across 5 dimensions (0-10 each). Identify weak spots before sending to a model.

```json
{ "prompt": "implement a login system" }
```

**Returns:** `total_score` (0-50), `score_normalized` (0-100), `dimensions`, `weak_spots`, `suggestions`

---

### `optimize_prompt_loop`
Iteratively optimize until a target score is reached or diminishing returns kick in. Full history included.

```json
{
  "prompt": "make an api for users",
  "target_score": 40,
  "max_iterations": 5,
  "language": "python"
}
```

**Returns:** `final_prompt`, `initial_score`, `final_score`, `score_normalized_before`, `score_normalized_after`, `engine_used`, `stopped_reason`, `history`

---

### `optimize_and_run` ⚡ Meta-tool
One call: optimize → decompose → generate code prompts per subtask. Everything an agent needs to begin execution.

```json
{
  "task": "build a user auth service",
  "language": "python",
  "agent_type": "code_agent"
}
```

**Returns:** `optimized_task`, `optimization_stats`, `decomposition`, `subtask_prompts` (each with `code_prompt` + `usage_hint`)

---

### `decompose_task`
Break a complex task into ordered, atomic subtasks with dependency tracking.

```json
{
  "task": "Implement JWT authentication with refresh token rotation",
  "agent_type": "code_agent"
}
```

**Returns:** `subtasks` (with `id`, `title`, `prompt`, `dependencies`, `estimated_complexity`), `execution_order`, `total_complexity`

---

### `generate_code_prompt`
Generate a production-ready, language-specific code prompt with role, constraints, and best practices.

```json
{
  "objective": "implement a rate limiter using Redis",
  "language": "python",
  "framework": "FastAPI"
}
```

---

### `start_optimization_session` / `continue_optimization_session`
Stateful, multi-turn optimization with optional agent feedback between rounds. Sessions expire after 30 minutes.

```json
// Start
{ "task": "refactor the database layer", "target_score": 80 }

// Continue
{ "session_id": "abc-123", "feedback": "Also add retry logic for transient errors." }
```

---

### `prompt-optimizer://health` (Resource)
Read the server health status, engine mode, and available tool list.

---

## CLI Usage

```bash
# Analyze a prompt
prompt-optimizer analyze "fix the bug"

# Optimize with language hints
prompt-optimizer optimize "build a REST API" --language python

# Full iterative loop
prompt-optimizer optimize "write a cache module" --loop --target-score 40

# JSON output for piping
prompt-optimizer optimize "describe the task" --json | jq .optimization.score_after
```

---

## Development

```bash
git clone https://github.com/yusufkucukates/mcp-prompt-optimizer
cd mcp-prompt-optimizer
pip install -e ".[dev]"

make test        # pytest with coverage
make lint        # ruff check
make typecheck   # mypy --strict
make check       # all three
```

---

## Why This Exists

Most AI agents send raw, vague prompts directly to the model. A prompt that scores 10/100 produces output that scores 10/100. This server intercepts that before it happens.

- **Zero-dependency offline mode** — the rule engine runs without any API calls, adding < 5ms latency.
- **Optional LLM enhancement** — plug in Anthropic or OpenAI to close the remaining gap on hard prompts.
- **8 composable tools** — from single-shot optimization to full agentic pipelines with decomposition.
- **Works where you work** — Claude Code, Cursor, any MCP-compatible client.

---

## Roadmap

- [ ] Streaming optimization (SSE for long prompts)
- [ ] Custom rule sets via TOML configuration
- [ ] Prompt library with searchable templates
- [ ] Team analytics: track score distributions across sessions
- [ ] VS Code extension for inline prompt scoring

---

## License

MIT © [Yusuf Kucukates](https://github.com/yusufkucukates)
