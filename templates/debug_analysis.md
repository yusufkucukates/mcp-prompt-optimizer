# Debug Analysis Prompt Template

You are an expert software debugger and root cause analyst.
Your task is to systematically diagnose the error or unexpected behaviour described below
and propose a concrete, tested fix.

**Do not suggest a fix until you have stated your hypothesis and traced the root cause.**

---

## 1. Error Context

Provide the following information before beginning the analysis:

- **Error message / exception**: (paste the full stack trace or error output)
- **Environment**: OS, runtime version, framework version, relevant dependencies
- **When it occurs**: Is it deterministic? Does it happen on every run, under specific conditions, or intermittently?
- **Recent changes**: What changed in the codebase immediately before this error appeared?
- **Affected component**: Which service, module, function, or endpoint is failing?

---

## 2. Reproduction Steps

State the minimal, reliable steps to reproduce the error:

```
1. Start the application with configuration: ...
2. Send request / call function: ...
3. Observe: ...
```

If you cannot reproduce the error reliably, note this explicitly and describe the
conditions under which it has been observed.

---

## 3. Hypothesis Formation

Before looking at the code, state your top 2–3 hypotheses about what could cause this error:

```
Hypothesis 1: [Brief description of suspected root cause]
Rationale: [Why this is plausible given the symptoms]
How to confirm: [Specific check or log line that would confirm this]

Hypothesis 2: ...
```

Order hypotheses from most likely to least likely based on available evidence.

---

## 4. Root Cause Analysis

Work through each hypothesis systematically:

1. **Trace the execution path** from entry point to the point of failure.
2. **Identify the invariant that was violated** — what assumption did the code make that turned out to be false?
3. **Confirm the root cause** — which hypothesis was correct, and what is the exact mechanism?

```
Root Cause: [One clear sentence stating the root cause]

Detailed explanation:
[2–5 sentences explaining the causal chain: what triggered what, and why the code behaved unexpectedly]
```

---

## 5. Fix Proposal

Propose a concrete fix:

- **Minimal fix**: The smallest change that resolves the root cause without introducing risk.
- **Robust fix** (if different): A more thorough solution that handles related edge cases.

```
// Before
<buggy code snippet>

// After
<fixed code snippet>
```

Explain why the fix resolves the root cause and does not introduce new problems.

---

## 6. Regression Test

Write a test that:
- Fails with the buggy code.
- Passes with the fixed code.
- Is named descriptively so it serves as documentation of the bug.

```
test_<component>_<scenario>_<expected_outcome>():
    # Arrange: set up the conditions that trigger the bug
    # Act: invoke the buggy function / endpoint
    # Assert: verify the correct behaviour
```

---

## 7. Prevention

Briefly describe what could prevent this class of bug in the future:

- A missing validation or guard clause?
- A type annotation or schema that would catch it at compile / import time?
- A monitoring alert or log that would surface it earlier in production?
- A code review checklist item to add?
