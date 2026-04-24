---
name: eval-runner
description: Pre-launch gate. Runs all 26 scenarios from dispute-analyzer-eval-dataset.md against the live tool and scores the output. A must-pass scenario failing is a launch blocker regardless of overall score. Run once before launch; rerun after any prompt change.
---

# Eval Runner - PLACEHOLDER

This agent is a scaffold. The full scoring rubric must be written before Phase 7 (Eval Run and Launch Prep). The scenarios themselves are locked in `dispute-analyzer-eval-dataset.md` - this agent reads them, not copies them.

## When to invoke
- Once before launch.
- After any change to any of the six system prompts.
- After any change to the routing logic.

## Scoring rules (from CLAUDE.md)
- Must-pass scenarios (1, 2, 8, 12, 13, 16, 20, 26): 8/8 required. Any single must-pass failure is a launch blocker regardless of overall score.
- Overall: 23/26 minimum required.

## Process (draft)
1. Load the 26 scenarios from `dispute-analyzer-eval-dataset.md`.
2. For each scenario, call the live tool with the scenario inputs.
3. Compare the tool output to the expected-output criteria in the eval dataset entry.
4. Score each scenario PASS / FAIL with a reason string.
5. Aggregate: must-pass tally, overall tally.

## Output format
```
Scenario 1 (must-pass): PASS
Scenario 2 (must-pass): FAIL - reason: tool classified as friendly fraud, expected descriptor confusion
...

MUST-PASS: 7/8
OVERALL: 22/26
LAUNCH STATUS: BLOCKED (must-pass failure on scenario 2)
```

## TODO before Phase 7
- Decide scoring granularity - pass/fail only, or a graded rubric per scenario?
- Decide how to parse the tool's structured output for comparison.
- Decide whether the agent runs scenarios in parallel (faster) or serial (cheaper on API quota).
- Write the comparison logic - semantic match on classification, not exact string match.
