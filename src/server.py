"""Main MCP server entry point for prompt-optimizer-mcp.

Registers 5 tools and all template resources using the MCP low-level Server API.
Transport: stdio (compatible with Claude Code and Cursor MCP integration).
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl

from src.resources.template_manager import TemplateManager
from src.tools.analyze_prompt import analyze_prompt
from src.tools.decompose_task import decompose_task
from src.tools.generate_code_prompt import generate_code_prompt
from src.tools.optimize_loop import optimize_prompt_loop
from src.tools.optimize_prompt import optimize_prompt

# ---------------------------------------------------------------------------
# Server and resource manager instances
# ---------------------------------------------------------------------------

SERVER_NAME = "prompt-optimizer-mcp"
SERVER_VERSION = "0.1.0"

server: Server = Server(SERVER_NAME)
template_manager: TemplateManager = TemplateManager()

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
                    "Supported: dotnet, python, go, java, typescript."
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
}

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[types.Tool] = [
    types.Tool(
        name="optimize_prompt",
        description=(
            "Optimize a prompt by detecting vague instructions, adding missing context, "
            "injecting role definitions, and applying language-specific best practices. "
            "Returns the improved prompt, a summary of changes, and before/after quality scores."
        ),
        inputSchema=TOOL_SCHEMAS["optimize_prompt"],
    ),
    types.Tool(
        name="decompose_task",
        description=(
            "Break down a complex task into sequential, atomic subtasks with dependency tracking. "
            "Each subtask includes a self-contained prompt, complexity estimate, and dependency list. "
            "Output is structured JSON suitable for feeding directly into an agentic loop."
        ),
        inputSchema=TOOL_SCHEMAS["decompose_task"],
    ),
    types.Tool(
        name="generate_code_prompt",
        description=(
            "Generate a production-ready prompt for a code generation task. "
            "Includes role definition, objective, constraints, style guide, best practices, "
            "output format, and TDD instructions tailored to the specified language."
        ),
        inputSchema=TOOL_SCHEMAS["generate_code_prompt"],
    ),
    types.Tool(
        name="analyze_prompt",
        description=(
            "Score a prompt across 5 quality dimensions (0-10 each): "
            "clarity, specificity, context, output_definition, and actionability. "
            "Identifies weak spots and returns concrete improvement suggestions."
        ),
        inputSchema=TOOL_SCHEMAS["analyze_prompt"],
    ),
    types.Tool(
        name="optimize_prompt_loop",
        description=(
            "Iteratively optimize a prompt across multiple rounds until a quality target is reached, "
            "diminishing returns are detected, or the iteration cap is hit. "
            "Returns the complete optimization history with per-round scores, diffs, and changes — "
            "so you can see exactly how the prompt improved at each step. "
            "Use this for agentic pipelines where prompt quality is critical."
        ),
        inputSchema=TOOL_SCHEMAS["optimize_prompt_loop"],
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
    """Dispatch a tool call to the corresponding module function.

    Args:
        name: Tool name as registered.
        arguments: Input arguments from the MCP client.

    Returns:
        A list containing a single TextContent with the JSON-encoded result.
    """
    try:
        result = _dispatch_tool(name, arguments)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as exc:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(exc), "tool": name}, indent=2),
            )
        ]


def _dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Route a tool call to the appropriate pure function.

    Args:
        name: Tool name.
        arguments: Validated input dict.

    Returns:
        The tool's result dict.

    Raises:
        ValueError: For unknown tool names or missing required arguments.
    """
    if name == "optimize_prompt":
        _require_fields(arguments, ["prompt"], name)
        return optimize_prompt(
            prompt=arguments["prompt"],
            context=arguments.get("context"),
            language=arguments.get("language"),
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
        kwargs: dict[str, Any] = {"prompt": arguments["prompt"]}
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
        return optimize_prompt_loop(**kwargs)

    raise ValueError(f"Unknown tool: '{name}'")


def _require_fields(arguments: dict[str, Any], fields: list[str], tool_name: str) -> None:
    """Raise ValueError/TypeError if any required field is missing or not a string."""
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


@server.list_resources()  # type: ignore[no-untyped-call, untyped-decorator]
async def handle_list_resources() -> list[types.Resource]:
    """Return all available prompt template resources."""
    templates = template_manager.list_templates()
    return [
        types.Resource(
            uri=AnyUrl(t["uri"]),
            name=t["name"],
            mimeType=t["mime_type"],
            description=f"Prompt template: {t['name'].replace('_', ' ').title()}",
        )
        for t in templates
    ]


@server.read_resource()  # type: ignore[no-untyped-call, untyped-decorator]
async def handle_read_resource(uri: AnyUrl) -> str:
    """Return the markdown content of a prompt template resource.

    Args:
        uri: Resource URI of the form ``prompt-template://{name}``.

    Returns:
        Raw markdown content of the template file.

    Raises:
        ValueError: If the URI scheme is unrecognised.
        FileNotFoundError: If no template with the given name exists.
    """
    uri_str = str(uri)
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
    """Entry point for the prompt-optimizer-mcp server.

    Prints startup information to stderr so it does not interfere with
    the stdio MCP transport on stdout.
    """
    template_count = len(template_manager.list_templates())
    tool_count = len(TOOL_DEFINITIONS)

    print(
        f"Starting {SERVER_NAME} v{SERVER_VERSION}",
        file=sys.stderr,
    )
    print(
        f"  Tools registered    : {tool_count}",
        file=sys.stderr,
    )
    print(
        f"  Resources available : {template_count} template(s)",
        file=sys.stderr,
    )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
