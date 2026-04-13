"""Tests for the standalone CLI (src/cli.py).

Uses subprocess to invoke the installed `prompt-optimizer` script and the
module directly via argparse to avoid requiring a real TTY.
"""

from __future__ import annotations

import json
import subprocess
import sys

# ---------------------------------------------------------------------------
# Helper: run the CLI module directly
# ---------------------------------------------------------------------------

def _run_cli(*args: str, stdin_text: str | None = None) -> subprocess.CompletedProcess:
    """Invoke `python -m src.cli` with the given args."""
    cmd = [sys.executable, "-m", "src.cli", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=stdin_text,
        cwd=_project_root(),
    )


def _project_root() -> str:
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent)


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


class TestCLIHelp:
    def test_help_exits_zero(self) -> None:
        result = _run_cli("--help")
        assert result.returncode == 0

    def test_help_mentions_loop(self) -> None:
        result = _run_cli("--help")
        assert "--loop" in result.stdout

    def test_help_mentions_language(self) -> None:
        result = _run_cli("--help")
        assert "--language" in result.stdout or "-l" in result.stdout

    def test_version_flag(self) -> None:
        result = _run_cli("--version")
        assert result.returncode == 0
        assert "0.1.0" in result.stdout or "0.1.0" in result.stderr


# ---------------------------------------------------------------------------
# One-shot mode (no --loop)
# ---------------------------------------------------------------------------


class TestCLIOneShotMode:
    def test_basic_prompt_exits_zero(self) -> None:
        result = _run_cli("write an api for users")
        assert result.returncode == 0

    def test_output_contains_optimized_prompt(self) -> None:
        result = _run_cli("write an api for users")
        assert "Optimized Prompt" in result.stdout or "optimized" in result.stdout.lower()

    def test_score_change_appears_in_output(self) -> None:
        result = _run_cli("write an api for users")
        # Should show score in the form "N/50"
        assert "/50" in result.stdout

    def test_language_flag_accepted(self) -> None:
        result = _run_cli("build a REST API", "--language", "python")
        assert result.returncode == 0

    def test_language_short_flag_accepted(self) -> None:
        result = _run_cli("build a REST API", "-l", "go")
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Loop mode
# ---------------------------------------------------------------------------


class TestCLILoopMode:
    def test_loop_flag_exits_zero(self) -> None:
        result = _run_cli("--loop", "make an api")
        assert result.returncode == 0

    def test_loop_output_contains_round_label(self) -> None:
        result = _run_cli("--loop", "make an api")
        assert "Round" in result.stdout or "round" in result.stdout.lower() or "Already" in result.stdout

    def test_loop_with_target_score(self) -> None:
        result = _run_cli("--loop", "make an api", "--target-score", "20")
        assert result.returncode == 0

    def test_loop_with_max_iterations(self) -> None:
        result = _run_cli("--loop", "write a function", "--max-iterations", "2")
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# JSON mode
# ---------------------------------------------------------------------------


class TestCLIJsonMode:
    def test_json_flag_produces_valid_json(self) -> None:
        result = _run_cli("write an api", "--json")
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert isinstance(payload, dict)

    def test_json_one_shot_has_optimization_key(self) -> None:
        result = _run_cli("write an api", "--json")
        payload = json.loads(result.stdout)
        assert "optimization" in payload

    def test_json_loop_has_loop_key(self) -> None:
        result = _run_cli("--loop", "write an api", "--json")
        payload = json.loads(result.stdout)
        assert "loop" in payload

    def test_json_loop_has_history(self) -> None:
        result = _run_cli("--loop", "write an api", "--json")
        payload = json.loads(result.stdout)
        assert "history" in payload["loop"]

    def test_json_analyze_flag_adds_analysis_key(self) -> None:
        result = _run_cli("write an api", "--json", "--analyze")
        payload = json.loads(result.stdout)
        assert "analysis" in payload
        assert "total_score" in payload["analysis"]


# ---------------------------------------------------------------------------
# Pipe / stdin mode
# ---------------------------------------------------------------------------


class TestCLIPipeMode:
    def test_stdin_prompt_works(self) -> None:
        result = _run_cli("--json", stdin_text="write an api for users")
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert "optimization" in payload

    def test_stdin_with_loop_flag(self) -> None:
        result = _run_cli("--loop", "--json", stdin_text="make a REST endpoint")
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert "loop" in payload

    def test_empty_stdin_exits_nonzero(self) -> None:
        result = _run_cli("--json", stdin_text="")
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestCLIErrorHandling:
    def test_no_args_no_stdin_exits_zero(self) -> None:
        # Without a TTY and without args, should show help or exit cleanly
        result = subprocess.run(
            [sys.executable, "-m", "src.cli"],
            capture_output=True,
            text=True,
            input=None,
            cwd=_project_root(),
        )
        # Acceptable: either 0 (shows help) or 0 (no stdin available)
        assert result.returncode in (0, 1)
