---
name: architecture-validator
description: Pre-launch gate. Confirms all eight required architecture patterns from CLAUDE.md are present in the codebase before the tool goes live. Run once before launch. All eight must be confirmed; anything missing is a launch blocker.
---

# Architecture Validator - PLACEHOLDER

This agent is a scaffold. The full system prompt must be written before Phase 7 (Eval Run and Launch Prep). The list of eight patterns to validate is locked by CLAUDE.md - do not add or remove from that list without updating the CLAUDE.md hard rules section first.

## When to invoke
Once, before going live. Runs as part of the pre-launch gate alongside the eval runner.

## The eight required patterns
Each must be confirmed present, with the file path and line range where it lives. If any are missing, the launch is blocked.

1. **Routing** - first Claude call classifies dispute type and selects the correct analysis pipeline.
2. **Parallelization** - four simultaneous Claude calls via `asyncio.gather()` covering delivery/fulfillment, customer behavior, transaction risk, reason code analysis.
3. **Evaluator-Optimizer** - a second Claude call validates the recommendation against quality criteria, loops up to three iterations on failure.
4. **Structured output with citations** - every claim in the output traces to a named source.
5. **MCP tool use** - Stripe official MCP server connected AND a custom Python delivery status MCP server built for this project and wired in.
6. **Prompt eval pipeline** - scored test cases run against the 26-scenario eval dataset, not cherry-picked demos.
7. **Temperature 0.1** - set on all six Claude API calls, with explanatory code comments.
8. **Prompt caching** - `cache_control` ephemeral present on all six system prompts.

## Output format
Return a checklist with file:line evidence:

```
PATTERN 1 - Routing: PRESENT at src/router.py:14-48
PATTERN 2 - Parallelization: PRESENT at src/pipeline.py:82-110
PATTERN 3 - Evaluator-Optimizer: PRESENT at src/evaluator.py:22-95
...
```

End with `ALL EIGHT CONFIRMED - LAUNCH APPROVED` or `MISSING: <pattern numbers> - LAUNCH BLOCKED`.

## TODO before Phase 7
- Write the actual validation logic as grep patterns or reading specific files.
- Decide whether this agent also validates the README explains each pattern (required for the Sardine-grade hiring-manager read).
