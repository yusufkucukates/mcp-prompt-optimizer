"""Standalone CLI for prompt-optimizer-mcp.

Provides one-click prompt optimization and agentic loop mode without
requiring an MCP client. Works as both a standard CLI and in pipe mode.

Usage examples::

    # 1-click optimization
    prompt-optimizer "write an api for user management"

    # Iterative loop mode
    prompt-optimizer --loop "write an api" --target-score 40

    # Language-aware optimization
    prompt-optimizer "build a REST API" --language python

    # Machine-readable JSON output (for CI/pipelines)
    prompt-optimizer --loop "my prompt" --json

    # Pipe mode
    echo "fix user login" | prompt-optimizer --loop
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap

from src.tools.analyze_prompt import analyze_prompt
from src.tools.optimize_loop import (
    STOP_ALREADY_OPTIMAL,
    optimize_prompt_loop,
)
from src.tools.optimize_prompt import optimize_prompt

# ---------------------------------------------------------------------------
# ANSI colour helpers (disabled when not a TTY or --json is set)
# ---------------------------------------------------------------------------

_USE_COLOUR = sys.stdout.isatty()

_RESET = "\033[0m" if _USE_COLOUR else ""
_BOLD = "\033[1m" if _USE_COLOUR else ""
_GREEN = "\033[32m" if _USE_COLOUR else ""
_YELLOW = "\033[33m" if _USE_COLOUR else ""
_CYAN = "\033[36m" if _USE_COLOUR else ""
_RED = "\033[31m" if _USE_COLOUR else ""
_DIM = "\033[2m" if _USE_COLOUR else ""


def _colour(text: str, code: str) -> str:
    if not _USE_COLOUR:
        return text
    return f"{code}{text}{_RESET}"


def _score_bar(score: int, total: int = 50, width: int = 20) -> str:
    """ASCII progress bar for a score value."""
    filled = round(score / total * width)
    bar = "█" * filled + "░" * (width - filled)
    pct = round(score / total * 100)
    return f"[{bar}] {score}/{total} ({pct}%)"


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _print_analysis(result: dict) -> None:
    score = result["total_score"]
    colour = _GREEN if score >= 35 else _YELLOW if score >= 20 else _RED
    print(f"\n{_BOLD}Prompt Analysis{_RESET}")
    print(f"  Score : {_colour(_score_bar(score), colour)}")
    print("  Dims  : ", end="")
    dims = result["dimensions"]
    parts = [f"{k[:3]}={v}" for k, v in dims.items()]
    print("  ".join(parts))
    if result["weak_spots"]:
        print(f"  Weak  : {_colour(', '.join(result['weak_spots']), _YELLOW)}")


def _print_one_shot(result: dict) -> None:
    before = result["score_before"]
    after = result["score_after"]
    delta = after - before
    delta_str = f"+{delta}" if delta >= 0 else str(delta)
    colour = _GREEN if delta > 5 else _YELLOW if delta > 0 else _DIM

    print(f"\n{_BOLD}Optimization Result{_RESET}")
    print(f"  Score : {before}/50  →  {after}/50  ({_colour(delta_str, colour)} pts)")
    if result["changes_summary"]:
        print(f"  Changes ({len(result['changes_summary'])}):")
        for change in result["changes_summary"]:
            print(f"    {_colour('•', _CYAN)} {change}")

    if result.get("diff"):
        print(f"\n{_DIM}--- diff ---{_RESET}")
        for line in result["diff"].splitlines()[:30]:
            if line.startswith("+"):
                print(_colour(line, _GREEN))
            elif line.startswith("-"):
                print(_colour(line, _RED))
            else:
                print(_colour(line, _DIM))
        if len(result["diff"].splitlines()) > 30:
            print(_colour("  ... (more lines in --json output)", _DIM))

    print(f"\n{_BOLD}Optimized Prompt:{_RESET}")
    print(textwrap.indent(result["optimized_prompt"], "  "))


def _print_loop(result: dict) -> None:
    initial = result["initial_score"]
    final = result["final_score"]
    total = result["total_improvement"]
    reason = result["stopped_reason"]
    iters = result["iterations_used"]

    reason_labels = {
        "target_score_reached": _colour("target score reached", _GREEN),
        "already_optimal": _colour("already optimal", _GREEN),
        "diminishing_returns": _colour("diminishing returns", _YELLOW),
        "max_iterations": _colour("max iterations hit", _YELLOW),
    }

    print(f"\n{_BOLD}Loop Optimization{_RESET}")
    print(f"  Initial score : {initial}/50")

    if reason == STOP_ALREADY_OPTIMAL:
        print(f"  {_colour('Already above target — no rounds needed.', _GREEN)}")
        print(f"\n{_BOLD}Prompt (unchanged):{_RESET}")
        print(textwrap.indent(result["final_prompt"], "  "))
        return

    for it in result["history"]:
        delta = it["improvement"]
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        colour = _GREEN if delta > 5 else _YELLOW if delta > 0 else _DIM
        print(
            f"\n  {_BOLD}Round {it['round']}{_RESET}  "
            f"{it['score'] - delta}/50  →  {it['score']}/50  "
            f"({_colour(delta_str, colour)} pts)"
        )
        for change in it.get("changes", []):
            print(f"    {_colour('•', _CYAN)} {change}")

    total_colour = _GREEN if total > 10 else _YELLOW if total > 0 else _DIM
    print(
        f"\n  {_BOLD}Final:{_RESET} {initial}/50  →  {final}/50  "
        f"({_colour(f'+{total}', total_colour)} pts in {iters} round{'s' if iters != 1 else ''})"
    )
    print(f"  Stopped : {reason_labels.get(reason, reason)}")

    print(f"\n{_BOLD}Optimized Prompt:{_RESET}")
    print(textwrap.indent(result["final_prompt"], "  "))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prompt-optimizer",
        description=(
            "Score, rewrite, and iteratively optimize prompts — "
            "instantly, offline, zero API keys."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            examples:
              prompt-optimizer "write an api for users"
              prompt-optimizer --loop "write an api" --target-score 40
              prompt-optimizer "build a REST API" --language python
              echo "my prompt" | prompt-optimizer --loop --json
            """
        ),
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help=(
            "Prompt text to optimize. If omitted, reads from stdin "
            "(useful for pipe mode: echo 'my prompt' | prompt-optimizer)."
        ),
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        default=False,
        help="Run iterative loop mode (default: single-pass optimization).",
    )
    parser.add_argument(
        "--language",
        "-l",
        metavar="LANG",
        default=None,
        help=(
            "Programming language for language-specific hints. "
            "Supported: python, dotnet, go, java, typescript "
            "(aliases: py, c#, js, ts, golang)."
        ),
    )
    parser.add_argument(
        "--context",
        "-c",
        metavar="TEXT",
        default=None,
        help="Background context injected into the prompt.",
    )
    parser.add_argument(
        "--target-score",
        type=int,
        default=40,
        metavar="N",
        help="(Loop mode) Target quality score 0-50. Default: 40.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        metavar="N",
        help="(Loop mode) Maximum optimization rounds. Default: 5.",
    )
    parser.add_argument(
        "--min-improvement",
        type=int,
        default=2,
        metavar="N",
        help="(Loop mode) Min score gain per round before stopping. Default: 2.",
    )
    parser.add_argument(
        "--analyze",
        "-a",
        action="store_true",
        default=False,
        help="Show quality analysis of the input prompt before optimizing.",
    )
    parser.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        default=False,
        help="Output raw JSON instead of formatted text (for pipelines).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="prompt-optimizer-mcp 0.1.0",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    # Resolve prompt text: positional arg or stdin
    prompt_text: str | None = args.prompt
    if prompt_text is None:
        if not sys.stdin.isatty():
            prompt_text = sys.stdin.read().strip()
        else:
            parser.print_help()
            sys.exit(0)

    if not prompt_text:
        print("Error: prompt text is empty.", file=sys.stderr)
        sys.exit(1)

    try:
        if args.output_json:
            _run_json_mode(args, prompt_text)
        else:
            _run_text_mode(args, prompt_text)
    except (TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run_json_mode(args: argparse.Namespace, prompt_text: str) -> None:
    """Emit a single JSON object to stdout."""
    payload: dict = {}

    if args.analyze:
        payload["analysis"] = analyze_prompt(prompt_text)

    if args.loop:
        payload["loop"] = optimize_prompt_loop(
            prompt=prompt_text,
            language=args.language,
            context=args.context,
            target_score=args.target_score,
            max_iterations=args.max_iterations,
            min_improvement=args.min_improvement,
        )
    else:
        payload["optimization"] = optimize_prompt(
            prompt=prompt_text,
            language=args.language,
            context=args.context,
        )

    print(json.dumps(payload, indent=2))


def _run_text_mode(args: argparse.Namespace, prompt_text: str) -> None:
    """Print human-friendly formatted output."""
    if args.analyze:
        analysis = analyze_prompt(prompt_text)
        _print_analysis(analysis)

    if args.loop:
        result = optimize_prompt_loop(
            prompt=prompt_text,
            language=args.language,
            context=args.context,
            target_score=args.target_score,
            max_iterations=args.max_iterations,
            min_improvement=args.min_improvement,
        )
        _print_loop(result)
    else:
        result = optimize_prompt(
            prompt=prompt_text,
            language=args.language,
            context=args.context,
        )
        _print_one_shot(result)

    print()


if __name__ == "__main__":
    main()
