# Retina Advisors Dispute Analyzer - CLAUDE.md

## What This Project Is
AI-powered dispute analysis tool for DTC Stripe merchants. Single dispute in, structured expert recommendation out. Portfolio piece targeting fraud SaaS hiring managers (Sardine, Socure, Sift, Stripe, Alloy). Live at retinaadvisors.com.

---

## Current State

**Phase:** Pre-code. No application code has been written yet. This directory currently holds reference documents only.

**Pre-code gate artifacts present in repo:**
- retina-advisors-prompt-system.md - all six prompts assembled
- dispute-analyzer-eval-dataset.md - 26 scenarios with must-pass designations
- retina-advisors-prompting-skill.md - extension patterns, voice standards, quality control
- dispute-analyzer-design-decisions.md - full analytical framework

**Pre-code gate items needing verification before coding begins:**
- Stripe MCP field research - confirm input form maps to real Stripe dispute fields

**Planned infrastructure, not yet built:**
- .claude/agents/ subagents (code reviewer, architecture validator, eval runner)
- .claude/settings.json hooks (PostToolUse black/flake8, PreToolUse write blocker)
- /commit-push-pr custom slash command
- Python application code, requirements.txt, tests
- Git repository (git init pending)

---

## Hard Rules - Never Violate These

**Never write a line of application code until all pre-code gates are complete:**
- System prompt finalized and reviewed
- Eval dataset of 26 scenarios exists as a saved file
- Stripe MCP field research complete - input form validated against real Stripe dispute data
- Prompting skill document exists and is referenced

**Never simplify or collapse the required architecture.** If a time or complexity constraint pushes toward skipping a pattern, stop and flag it. Do not make the tradeoff silently.

**Never use em dashes** in any output - README, prompts, UI copy, comments, documentation. Single dashes only.

**Never invent Stripe fields.** Every input field must map to data Stripe actually surfaces on a dispute. If uncertain, research before building.

**Never commit secrets, API keys, or credentials.**

**Never commit without running the code reviewer subagent first.**

---

## Required Architecture - All Must Be Present

These are non-negotiable. A hiring manager reading the README and codebase must be able to identify all of them clearly.

1. **Routing** - first Claude call classifies dispute type, routes to the correct analysis pipeline
2. **Parallelization** - four simultaneous Claude calls via asyncio.gather(), one per evidence stream: delivery/fulfillment, customer behavior, transaction risk, reason code analysis
3. **Evaluator-Optimizer** - a second Claude call validates the recommendation against quality criteria and loops if it fails, maximum three iterations
4. **Structured output with citations** - every claim in the output report traces to a named source
5. **MCP tool use** - Stripe official MCP server + custom Python delivery status MCP server built for this project
6. **Prompt eval pipeline** - scored test cases against the 26-scenario eval dataset, not cherry-picked demos
7. **Temperature 0.1** - set from the first API call on all six prompts, documented in code comments explaining why
8. **Prompt caching** - cache_control ephemeral on all six system prompts from the first request

**The six prompts** (canonical list for items 7 and 8):
1. Routing - classifies dispute type and selects pipeline
2. Delivery/fulfillment analysis (parallel)
3. Customer behavior analysis (parallel)
4. Transaction risk analysis (parallel)
5. Reason code analysis (parallel)
6. Evaluator-Optimizer - validates recommendation against quality criteria, loops up to three times

---

## Workflow - Follow This Every Session

**Explore before Plan before Code. Never skip steps.**

1. Explore - read the relevant prompt files, design decisions document, and prompting skill before touching anything
2. Plan - use Plan Mode (Shift+Tab) for any feature that touches more than one file. Get approval before writing code.
3. Code - implement the plan. If Claude hits the same issue twice, save the solution to this file with #.
4. Commit - run code reviewer subagent first, then /commit-push-pr (both are planned but not yet built)

**Context management:**
- /compact when deep in a feature and approaching context limit
- /clear when switching to a completely different component
- Turn off unused MCP servers during focused work - they burn context

---

## Quality Gates

### Pre-commit gate (every commit)
Run the code reviewer subagent. It will be defined in .claude/agents/ (planned, not yet built).
Subagent must return zero blocking issues before committing.

### Pre-launch gate (before going live)
Run the architecture validator subagent (planned, not yet built). All eight required patterns
must be confirmed present in the codebase.

Run the eval runner subagent (planned, not yet built) against all 26 scenarios:
- Must-pass scenarios (1, 2, 8, 12, 13, 16, 20, 26): 8/8 required
- Overall: 23/26 minimum required
- Any must-pass failure is a launch blocker regardless of overall score

Full quality gate details are in the prompting skill document.

### Pre-code gate (before any application code)
All items in the pre-code gates list above must be checked off.

---

## Hooks (Planned, not yet built)

Hooks enforce what CLAUDE.md can only suggest. Once built, these will be configured
in .claude/settings.json and run deterministically on every trigger.

PostToolUse hook - fires after any Python file edit:
- Runs black formatter on the edited file
- Runs flake8 and feeds any errors back to Claude

PreToolUse hook - fires before any file write:
- Blocks writes to .env files
- Blocks writes to production config files

Once built, these hooks will be checked into the repo. The whole team gets them.

---

## How to Work With Bryan

- Ask one question at a time. Never stack decisions.
- Engage honestly. Agree when Bryan is right, push back when something is wrong or suboptimal - never agree blindly just to move forward.
- Connect every technical concept to a fraud analogy. Routing = fraud rule triage. Parallelization = running card network rules and ML model simultaneously. Evaluator-Optimizer = backtesting a fraud rule before deploying it.
- Bryan needs to understand and explain every decision in a job interview. Build his understanding alongside the code, not just the code.
- Bryan is on Windows, uses GitHub Desktop, is comfortable in VS Code, and this is his first Claude Code project.

---

## Reference Documents

Canonical working copies live in this repo root (C:\Users\bshap\OneDrive\Desktop\Retina-Advisors\). Master copies also exist in C:\Users\bshap\OneDrive\Desktop\Fraud Consulting\, but treat the repo copies as authoritative during the build to avoid version drift.

- dispute-analyzer-design-decisions.md - full analytical framework, data architecture, input fields, output structure
- retina-advisors-prompt-system.md - all six prompts, assembled and ready
- dispute-analyzer-eval-dataset.md - 26 scenarios with must-pass designations
- retina-advisors-prompting-skill.md - extension patterns, voice standards, quality control
- Claude_Code_Course_Summary.md - Claude Code workflow reference

---

## Tech Stack
- Backend: Python (no code written yet, no requirements.txt, no test harness - pre-code phase)
- MCP: Stripe official MCP + custom Python MCP server for delivery status lookup (custom server not yet built)
- Hosted: retinaadvisors.com (domain secured, app not yet deployed)
- Repo: public GitHub (git init pending, will be initialized after CLAUDE.md updates land)
- Built with: Claude Code

No build, test, or run commands exist yet. Once Python code lands, this section should be updated with the actual commands.
