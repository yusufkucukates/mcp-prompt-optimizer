<!-- Thanks for contributing! Please fill in the sections below. -->

## Summary
<!-- What does this PR do? One or two sentences. -->

## Type of change
- [ ] Bug fix
- [ ] New feature (tool, rule, or template)
- [ ] Refactor / internal
- [ ] Docs / CI / tooling

## Checklist
- [ ] `make check` passes (ruff + mypy + pytest)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] New tool or rule has a test in `tests/`
- [ ] Tool descriptions in `TOOL_DEFINITIONS` are LLM-readable (imperative, include parameter names and accepted values)
- [ ] No `print()` to stdout in `src/` (use `print(..., file=sys.stderr)`)
- [ ] Tool modules in `src/tools/` do not import from `src/server.py`

## How to test
<!-- Commands to reproduce or verify the change. -->

## Related issues
Closes #
