"""Main MCP server entry point for prompt-optimizer-mcp.

Registers 8 tools and all template resources using the MCP low-level Server API.
Transport: stdio (compatible with Claude Code and Cursor MCP integration).
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl

from src.llm.base import LLMProvider
from src.llm.config import get_config
from src.llm.factory import get_provider
from src.log import log
from src.resources.template_manager import TemplateManager
from src.tools.analyze_prompt import analyze_prompt
from src.tools.decompose_task import decompose_task
from src.tools.generate_code_prompt import generate_code_prompt
from src.tools.optimize_and_run import optimize_and_run
from src.tools.optimize_loop import optimize_prompt_loop
from src.tools.optimize_prompt import optimize_prompt
from src.tools.session import continue_optimization_session, start_optimization_session

# ---------------------------------------------------------------------------
# Server and resource manager instances
# ---------------------------------------------------------------------------

SERVER_NAME = "prompt-optimizer-mcp"
SERVER_VERSION = "0.2.0"

server: Server = Server(SERVER_NAME)
template_manager: TemplateManager = TemplateManager()

# Initialise LLM provider once at startup (None when LLM is disabled or key not set)
_llm_config = get_config()
_llm_provider: LLMProvider | None = get_provider(_llm_config)
_server_start_time: float = time.time()

# ---------------------------------------------------------------------------
# Tool input schemas
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "optimize_prompt": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The original prompt text to optimize.",
            },
            "context": {
                "type": "string",
                "description": "Optional background context to inject into the prompt.",
            },
            "language": {
                "type": "string",
                "description": (
                    "Optional programming language for language-specific hints. "
                    "Supported: dotnet, python, go, java, typescript (and aliases)."
                ),
            },
        },
        "required": ["prompt"],
    },
    "decompose_task": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Natural-language description of the complex task to decompose.",
            },
            "agent_type": {
                "type": "string",
                "description": (
                    "Type of agent that will execute the subtasks. "
                    "Supported: code_agent, devops_agent, generic (default)."
                ),
            },
        },
        "required": ["task"],
    },
    "generate_code_prompt": {
        "type": "object",
        "properties": {
            "objective": {
                "type": "string",
                "description": "What the generated code should accomplish.",
            },
            "language": {
                "type": "string",
                "description": (
                    "Target programming language. "
                    "Supported: dotnet, python, go, java, typescript."
                ),
            },
            "framework": {
                "type": "string",
                "description": "Optional framework or library (e.g. FastAPI, ASP.NET Core).",
            },
            "style_guide": {
                "type": "string",
                "description": "Optional custom style instructions; overrides language defaults.",
            },
        },
        "required": ["objective", "language"],
    },
    "analyze_prompt": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The prompt text to analyze and score.",
            },
        },
        "required": ["prompt"],
    },
    "optimize_prompt_loop": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The starting prompt text to iteratively optimize.",
            },
            "language": {
                "type": "string",
                "description": (
                    "Optional programming language for language-specific hints. "
                    "Supported: dotnet, python, go, java, typescript (and aliases: "
                    "c#, csharp, js, ts, py, golang, kotlin)."
                ),
            },
            "context": {
                "type": "string",
                "description": "Optional background context injected in the first round.",
            },
            "target_score": {
                "type": "integer",
                "description": "Quality target (0-50). Loop stops when score reaches this. Default: 40.",
            },
            "max_iterations": {
                "type": "integer",
                "description": "Maximum number of optimization rounds. Default: 5.",
            },
            "min_improvement": {
                "type": "integer",
                "description": (
                    "Minimum score gain per round. Two consecutive rounds below this "
                    "threshold trigger a diminishing-returns stop. Default: 2."
                ),
            },
        },
        "required": ["prompt"],
    },
    "optimize_and_run": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "The raw task description to optimize and execute.",
            },
            "language": {
                "type": "string",
                "description": "Target programming language for code generation. Default: python.",
            },
            "agent_type": {
                "type": "string",
                "description": (
                    "Execution agent type for task decomposition. "
                    "Supported: code_agent (default), devops_agent, generic."
                ),
            },
            "context": {
                "type": "string",
                "description": "Optional background context injected during optimization.",
            },
        },
        "required": ["task"],
    },
    "start_optimization_session": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "The raw prompt or task to optimize over multiple rounds.",
            },
            "max_iterations": {
                "type": "integer",
                "description": "Maximum number of optimization rounds. Default: 5.",
            },
            "target_score": {
                "type": "integer",
                "description": "Normalized quality target (0-100). Default: 80.",
            },
            "language": {
                "type": "string",
                "description": "Optional programming language for language-specific optimization.",
            },
            "context": {
                "type": "string",
                "description": "Optional background context for the first round.",
            },
        },
        "required": ["task"],
    },
    "continue_optimization_session": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Session ID returned by start_optimization_session.",
            },
            "feedback": {
                "type": "string",
                "description": (
                    "Optional agent feedback to inject as context in this round. "
                    "Use this to guide the optimization based on your observations."
                ),
            },
        },
        "required": ["session_id"],
    },
}

# ---------------------------------------------------------------------------
# Tool definitions (LLM-actionable descriptions)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[types.Tool] = [
    types.Tool(
        name="optimize_prompt",
        description=(
            "Call this when you have a prompt that needs improvement before sending to another "
            "AI model or agent. Provide the raw prompt text; optionally specify a programming "
            "language for domain-specific improvements. Returns the improved prompt, a quality "
            "score comparison (before/after, 0-50 and 0-100 normalized), a line-by-line diff, "
            "and which engine was used (rules or hybrid). "
            "Use BEFORE decompose_task or generate_code_prompt for best results."
        ),
        inputSchema=TOOL_SCHEMAS["optimize_prompt"],
    ),
    types.Tool(
        name="decompose_task",
        description=(
            "Call this when you have a complex, multi-step task that needs to be broken down "
            "before execution. Provide a clear task description and the agent type that will "
            "execute it. Returns sequential atomic subtasks with dependency tracking, complexity "
            "estimates, and self-contained prompts for each step. "
            "Use AFTER optimize_prompt for best results."
        ),
        inputSchema=TOOL_SCHEMAS["decompose_task"],
    ),
    types.Tool(
        name="generate_code_prompt",
        description=(
            "Call this when you need a production-ready, language-specific prompt for a code "
            "generation task. Provide the objective and target language; optionally specify a "
            "framework and style guide. Returns a complete prompt with role definition, "
            "constraints, best practices, output format, and TDD instructions tailored to the "
            "specified language."
        ),
        inputSchema=TOOL_SCHEMAS["generate_code_prompt"],
    ),
    types.Tool(
        name="analyze_prompt",
        description=(
            "Call this when you want to measure the quality of a prompt before or after "
            "optimization. Returns a score across 5 dimensions (0-10 each): clarity, "
            "specificity, context, output_definition, and actionability. Also returns a "
            "normalized score (0-100), a list of weak dimensions, and concrete improvement "
            "suggestions for each weak spot."
        ),
        inputSchema=TOOL_SCHEMAS["analyze_prompt"],
    ),
    types.Tool(
        name="optimize_prompt_loop",
        description=(
            "Call this when you need the highest possible prompt quality and are willing to "
            "run multiple optimization rounds. Iteratively optimizes until a target score is "
            "reached, diminishing returns are detected, or the iteration cap is hit. "
            "Returns the complete optimization history with per-round scores, diffs, and "
            "changes so you can see exactly how the prompt improved at each step. "
            "Use this for agentic pipelines where prompt quality is critical."
        ),
        inputSchema=TOOL_SCHEMAS["optimize_prompt_loop"],
    ),
    types.Tool(
        name="optimize_and_run",
        description=(
            "Call this when you have a vague task description and want a complete, ready-to-execute "
            "agent plan in one call. Chains three steps automatically: (1) optimizes the task prompt, "
            "(2) decomposes it into ordered subtasks, (3) generates production-ready code prompts for "
            "each subtask. Returns everything needed to begin execution immediately — no further "
            "processing required."
        ),
        inputSchema=TOOL_SCHEMAS["optimize_and_run"],
    ),
    types.Tool(
        name="start_optimization_session",
        description=(
            "Call this when you want to iteratively improve a prompt across multiple agent turns "
            "with optional feedback between rounds. Creates a session, runs the first optimization "
            "round, and returns a session_id for subsequent calls. Use continue_optimization_session "
            "to run additional rounds. Sessions expire after 30 minutes of inactivity."
        ),
        inputSchema=TOOL_SCHEMAS["start_optimization_session"],
    ),
    types.Tool(
        name="continue_optimization_session",
        description=(
            "Call this to run the next round of an active optimization session started with "
            "start_optimization_session. Provide the session_id and optionally feedback about "
            "the current prompt. Returns the improved prompt, updated scores, and whether the "
            "session is complete. Check the 'done' field — when true, use the current_prompt."
        ),
        inputSchema=TOOL_SCHEMAS["continue_optimization_session"],
    ),
]

# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


@server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
async def handle_list_tools() -> list[types.Tool]:
    """Return the list of available tools."""
    return TOOL_DEFINITIONS


@server.call_tool()  # type: ignore[untyped-decorator]
async def handle_call_tool(
    name: str,
    arguments: dict[str, Any],
) -> list[types.TextContent]:
    """Dispatch a tool call to the corresponding module function."""
    t0 = time.time()
    try:
        result = await _dispatch_tool(name, arguments)
        duration_ms = round((time.time() - t0) * 1000)
        log("INFO", "tool_called", tool=name, duration_ms=duration_ms)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as exc:
        duration_ms = round((time.time() - t0) * 1000)
        log("ERROR", "tool_error", tool=name, error=str(exc), duration_ms=duration_ms)
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(exc), "tool": name}, indent=2),
            )
        ]


async def _dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Route a tool call to the appropriate pure function."""
    if name == "optimize_prompt":
        _require_fields(arguments, ["prompt"], name)
        return await optimize_prompt(
            prompt=arguments["prompt"],
            context=arguments.get("context"),
            language=arguments.get("language"),
            provider=_llm_provider,
            llm_threshold=_llm_config.threshold,
        )

    if name == "decompose_task":
        _require_fields(arguments, ["task"], name)
        return decompose_task(
            task=arguments["task"],
            agent_type=arguments.get("agent_type", "generic"),
        )

    if name == "generate_code_prompt":
        _require_fields(arguments, ["objective", "language"], name)
        return generate_code_prompt(
            objective=arguments["objective"],
            language=arguments["language"],
            framework=arguments.get("framework"),
            style_guide=arguments.get("style_guide"),
        )

    if name == "analyze_prompt":
        _require_fields(arguments, ["prompt"], name)
        return analyze_prompt(prompt=arguments["prompt"])

    if name == "optimize_prompt_loop":
        _require_fields(arguments, ["prompt"], name)
        kwargs: dict[str, Any] = {
            "prompt": arguments["prompt"],
            "provider": _llm_provider,
            "llm_threshold": _llm_config.threshold,
        }
        if "language" in arguments and arguments["language"] is not None:
            kwargs["language"] = arguments["language"]
        if "context" in arguments and arguments["context"] is not None:
            kwargs["context"] = arguments["context"]
        if "target_score" in arguments and arguments["target_score"] is not None:
            kwargs["target_score"] = int(arguments["target_score"])
        if "max_iterations" in arguments and arguments["max_iterations"] is not None:
            kwargs["max_iterations"] = int(arguments["max_iterations"])
        if "min_improvement" in arguments and arguments["min_improvement"] is not None:
            kwargs["min_improvement"] = int(arguments["min_improvement"])
        return await optimize_prompt_loop(**kwargs)

    if name == "optimize_and_run":
        _require_fields(arguments, ["task"], name)
        return await optimize_and_run(
            task=arguments["task"],
            language=arguments.get("language", "python"),
            agent_type=arguments.get("agent_type", "code_agent"),
            context=arguments.get("context"),
            provider=_llm_provider,
            llm_threshold=_llm_config.threshold,
        )

    if name == "start_optimization_session":
        _require_fields(arguments, ["task"], name)
        kwargs2: dict[str, Any] = {
            "task": arguments["task"],
            "provider": _llm_provider,
            "llm_threshold": _llm_config.threshold,
        }
        if "max_iterations" in arguments and arguments["max_iterations"] is not None:
            kwargs2["max_iterations"] = int(arguments["max_iterations"])
        if "target_score" in arguments and arguments["target_score"] is not None:
            kwargs2["target_score"] = int(arguments["target_score"])
        if "language" in arguments and arguments["language"] is not None:
            kwargs2["language"] = arguments["language"]
        if "context" in arguments and arguments["context"] is not None:
            kwargs2["context"] = arguments["context"]
        return await start_optimization_session(**kwargs2)

    if name == "continue_optimization_session":
        _require_fields(arguments, ["session_id"], name)
        return await continue_optimization_session(
            session_id=arguments["session_id"],
            feedback=arguments.get("feedback"),
            provider=_llm_provider,
            llm_threshold=_llm_config.threshold,
        )

    raise ValueError(f"Unknown tool: '{name}'")


def _require_fields(arguments: dict[str, Any], fields: list[str], tool_name: str) -> None:
    """Raise ValueError/TypeError if any required field is missing or wrong type."""
    missing = [f for f in fields if f not in arguments or arguments[f] is None]
    if missing:
        raise ValueError(
            f"Tool '{tool_name}' requires field(s): {', '.join(missing)}"
        )
    wrong_type = [f for f in fields if not isinstance(arguments[f], str)]
    if wrong_type:
        detail = ", ".join(
            f"{f}={type(arguments[f]).__name__!r}" for f in wrong_type
        )
        raise TypeError(
            f"Tool '{tool_name}': field(s) {', '.join(wrong_type)} must be strings "
            f"(got {detail})"
        )


# ---------------------------------------------------------------------------
# Resource handlers
# ---------------------------------------------------------------------------

_HEALTH_URI = "prompt-optimizer://health"


@server.list_resources()  # type: ignore[no-untyped-call, untyped-decorator]
async def handle_list_resources() -> list[types.Resource]:
    """Return all available prompt template resources plus the health endpoint."""
    resources: list[types.Resource] = [
        types.Resource(
            uri=AnyUrl(_HEALTH_URI),
            name="health",
            mimeType="application/json",
            description="Server health check: status, version, engine mode, and available tools.",
        )
    ]
    templates = template_manager.list_templates()
    for t in templates:
        resources.append(
            types.Resource(
                uri=AnyUrl(t["uri"]),
                name=t["name"],
                mimeType=t["mime_type"],
                description=f"Prompt template: {t['name'].replace('_', ' ').title()}",
            )
        )
    return resources


@server.read_resource()  # type: ignore[no-untyped-call, untyped-decorator]
async def handle_read_resource(uri: AnyUrl) -> str:
    """Return the content of a prompt template resource or the health JSON."""
    uri_str = str(uri)

    if uri_str == _HEALTH_URI:
        uptime = round(time.time() - _server_start_time)
        health: dict[str, Any] = {
            "status": "ok",
            "version": SERVER_VERSION,
            "engine": "hybrid" if _llm_provider is not None else "rules",
            "llm_available": _llm_provider is not None,
            "llm_provider": _llm_config.provider if _llm_provider is not None else None,
            "tools": [t.name for t in TOOL_DEFINITIONS],
            "templates": len(template_manager.list_templates()),
            "uptime_seconds": uptime,
        }
        return json.dumps(health, indent=2)

    name = template_manager.template_uri_to_name(uri_str)
    return template_manager.get_template(name)


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


async def _run() -> None:
    """Run the MCP server using stdio transport."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    """Entry point for the prompt-optimizer-mcp server."""
    template_count = len(template_manager.list_templates())
    tool_count = len(TOOL_DEFINITIONS)
    engine = "hybrid" if _llm_provider is not None else "rules"

    log(
        "INFO",
        "server_starting",
        name=SERVER_NAME,
        version=SERVER_VERSION,
        tools=tool_count,
        templates=template_count,
        engine=engine,
        llm_provider=_llm_config.provider if _llm_provider is not None else None,
    )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
