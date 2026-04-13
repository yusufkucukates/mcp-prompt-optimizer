"""Structured JSON logger for prompt-optimizer-mcp.

All output goes to ``sys.stderr`` so it never interferes with the MCP
stdio transport on ``stdout``.

Usage::

    from src.log import log
    log("INFO", "server_started", version="0.2.0", tools=7)
    log("INFO", "tool_called", tool="optimize_prompt", engine="hybrid",
        score_before=12, score_after=42, duration_ms=234)
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any


def log(level: str, message: str, **context: Any) -> None:
    """Emit a structured JSON log entry to stderr.

    Args:
        level:   Log level string (e.g. ``"INFO"``, ``"ERROR"``).
        message: Short human-readable description of the event.
        **context: Arbitrary key-value pairs added to the JSON payload.
    """
    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level,
        "message": message,
        **context,
    }
    print(json.dumps(entry), file=sys.stderr)
