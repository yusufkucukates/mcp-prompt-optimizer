# Installation Guide

This guide covers everything you need to run `mcp-prompt-optimizer` locally and connect it to Claude Code or Cursor.

---

## Prerequisites

- **Python 3.11 or higher** — check with `python3 --version`
- **git** — check with `git --version`
- A terminal (bash, zsh, PowerShell)

---

## 1. Clone and install

```bash
git clone https://github.com/yusufkucukates/mcp-prompt-optimizer
cd mcp-prompt-optimizer
pip install -e .
```

This installs the server in editable mode and registers the `prompt-optimizer-mcp` command.

### Optional: LLM enhancement

The rule engine works with zero API keys. To enable the optional LLM layer:

```bash
# Anthropic (Claude Haiku by default)
pip install -e ".[anthropic]"

# OpenAI (GPT-4o-mini by default)
pip install -e ".[openai]"

# Both providers
pip install -e ".[llm]"
```

### Development dependencies (tests, linting, type checking)

```bash
pip install -e ".[dev]"
```

---

## 2. MCP Client Configuration

### Claude Code (`~/.claude.json`)

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

To enable LLM enhancement, set `PROMPT_OPTIMIZER_LLM` to `"true"` and add your API key:

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

Create or update `.cursor/mcp.json` in your project root or home directory:

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

---

## 3. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PROMPT_OPTIMIZER_LLM` | `false` | Set to `true` to enable LLM enhancement |
| `PROMPT_OPTIMIZER_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `PROMPT_OPTIMIZER_API_KEY` | — | API key (falls back to `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) |
| `PROMPT_OPTIMIZER_MODEL` | provider default | Override the model name |
| `PROMPT_OPTIMIZER_THRESHOLD` | `80` | Normalized score (0-100) below which LLM triggers |

---

## 4. Verification

### Check the server version

```bash
python -c "from src.server import SERVER_VERSION; print(SERVER_VERSION)"
# Expected output: 0.2.0
```

### Run a quick CLI test

```bash
echo "write some code" | prompt-optimizer optimize --language python
```

You should see an optimized prompt printed to the terminal with a score comparison.

### Run the test suite

```bash
python -m pytest tests/ -q
# Expected: 204 passed
```

### Read the health resource (manual MCP test)

```bash
python -c "
import asyncio, json
from src.server import handle_read_resource
from pydantic import AnyUrl
result = asyncio.run(handle_read_resource(AnyUrl('prompt-optimizer://health')))
print(json.loads(result)['status'])
"
# Expected output: ok
```

---

## 5. Troubleshooting

### `command not found: prompt-optimizer-mcp`

The console script was not added to your PATH. This usually means the Python `bin/` directory is not in your PATH.

**Fix:**
```bash
# Find where pip installs scripts
python -m site --user-base
# Add <user-base>/bin to your PATH in ~/.zshrc or ~/.bashrc:
export PATH="$HOME/.local/bin:$PATH"
# Then reload:
source ~/.zshrc
```

If you installed inside a virtual environment, activate it first:
```bash
source .venv/bin/activate
```

---

### `ModuleNotFoundError: No module named 'mcp'`

The `mcp[cli]` core dependency is missing.

**Fix:**
```bash
pip install "mcp[cli]>=1.0.0"
# or reinstall the project
pip install -e .
```

---

### Server installed but not appearing in Claude Code / Cursor

The MCP client cannot find the server binary or the config path is wrong.

**Checklist:**
1. Confirm the command resolves: `which prompt-optimizer-mcp`
2. Use the absolute path in the config if needed:
   ```json
   { "command": "/Users/you/.local/bin/prompt-optimizer-mcp" }
   ```
3. Restart the MCP client completely after editing the config file.
4. Check that the config file is valid JSON (no trailing commas).
5. Confirm `stdio` transport — this server does **not** use HTTP/SSE.
