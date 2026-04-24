# Retina Advisors - Build Status

Update this file at the end of every session. A new chat session
reads this first to know exactly where the project stands.

Last updated: April 24, 2025 (Phase 1 complete)
Current phase: Ready for Phase 2 - Stripe MCP Connection

---

## How to Resume in a New Chat Session

Paste this at the start of any new Claude.ai or Claude Code session:

"I am building the Retina Advisors Dispute Analyzer. Read these
files in my Retina-Advisors project folder before we continue:
CLAUDE.md, build-status.md, and whichever phase documents are
relevant. Then tell me what you understand and ask what we are
working on today."

---

## Build Phases - Status

Phase 1 - Project Foundation
Status: COMPLETE
Started: April 24, 2025
Completed: April 24, 2025
Tasks:
- [x] CLAUDE.md updated with /init suggestions applied
- [x] Git repository initialized
- [x] GitHub public repo created
- [x] Basic Python project structure created
- [x] requirements.txt created
- [x] Folder structure established
- [x] .claude/settings.json created with hooks
- [x] .claude/agents/ folder created (placeholder files)
Notes: Claude Code ran /init and suggested six CLAUDE.md improvements.
All six accepted and applied. Repo initialized on main branch (renamed
from default master), pushed to https://github.com/bshap18-sys/Retina-Advisors.

Python scaffold:
- src/retina/ package, src/ layout
- tests/ with a smoke test that verifies package import
- requirements.txt (anthropic, mcp)
- requirements-dev.txt (black, flake8, pytest, pytest-asyncio)
- pyproject.toml with pytest pythonpath=src and asyncio_mode=auto
- .flake8 config aligned with black (max-line-length 100)
- Python 3.14.0 venv at .venv (gitignored), all deps install cleanly

Hooks:
- PreToolUse block-sensitive-writes.sh: refuses writes to .env files
  and production configs. Verified end-to-end.
- PostToolUse format-python.sh: runs black and flake8 on .py files via
  the project venv, no-ops when tools are unavailable. JSON input is
  parsed with grep/sed for zero runtime dependencies.

Agents are placeholders with TODO notes, fleshed out in later phases.

Phase 2 - Stripe MCP Connection
Status: NEXT UP
Tasks:
- [ ] Stripe MCP server added to Claude Code
- [ ] Test pull of dispute object confirmed
- [ ] Test pull of charge object expansion confirmed
- [ ] Test pull of customer history confirmed
- [ ] Data layer validated before building on top of it
Notes: Requires a Stripe test-mode API key. First move is adding
Stripe's official MCP server to Claude Code config. Blocked pre-code
gate: Stripe MCP field research - this phase closes it by confirming
every planned input form field maps to a real Stripe dispute/charge/
customer field.

Phase 3 - Custom Delivery MCP Server
Status: NOT STARTED
Tasks:
- [ ] Python MCP server file created
- [ ] Delivery status lookup tool defined
- [ ] Server tested locally
- [ ] Server connected to Claude Code
- [ ] Test lookup confirmed working
Notes: This is the piece that demonstrates Bryan can build MCP
servers, not just connect to existing ones. Portfolio critical.

Phase 4 - Prompt System Implementation
Status: NOT STARTED
Tasks:
- [ ] Python async architecture scaffolded
- [ ] All six prompts loaded from prompt system document
- [ ] Temperature 0.1 set on all six prompts
- [ ] Prompt caching headers added to all six
- [ ] asyncio.gather() wiring all four parallel calls
- [ ] Synthesis prompt receiving four JSON inputs correctly
- [ ] Evaluator prompt connected to synthesis output
- [ ] Scenario 1 from eval dataset run successfully
Notes: All six prompts are fully written and in
retina-advisors-prompt-system.md. Implementation is dropping
them into Python with the correct architecture around them.

Phase 5 - Evaluator Loop
Status: NOT STARTED
Tasks:
- [ ] Evaluator fires after synthesis prompt
- [ ] Revision loop wired with maximum three iterations
- [ ] Escalation with low confidence flag on loop timeout
- [ ] Scenario 26 (evaluator loop test) passes
Notes: Scenario 26 in the eval dataset is specifically designed
to test this loop. It must pass before moving to Phase 6.

Phase 6 - Input Form and Frontend
Status: NOT STARTED
Tasks:
- [ ] Merchant context form fields built
- [ ] Fulfillment data fields built
- [ ] Customer contact fields built
- [ ] Order context fields built
- [ ] Policy fields built
- [ ] Document upload section built
- [ ] Form connected to Python backend
- [ ] Full analysis flow working end to end
Notes: Clean and functional is the goal. Not fancy.
The analysis output is the product, not the UI.

Phase 7 - Eval Run and Launch Prep
Status: NOT STARTED
Tasks:
- [ ] All 26 eval scenarios run against live tool
- [ ] Must-pass scenarios (1,2,8,12,13,16,20,26): 8/8
- [ ] Overall score: 23/26 minimum
- [ ] README written with all eight architecture patterns explained
- [ ] Architecture diagram created and added to repo
- [ ] GitHub repo confirmed public
- [ ] Live demo accessible at retinaadvisors.com
- [ ] LinkedIn carousel post drafted
Notes: The README is as important as the code for the Sardine test.
A hiring manager who reads the README should understand the full
architecture without running the code.

---

## Key Decisions Made This Session

April 24, 2025:
- Six-prompt architecture finalized: synthesis, delivery analysis,
  customer behavior, transaction risk, reason code analysis,
  evaluator
- 26 eval scenarios built with must-pass designations
- Output format: Option B hybrid - verdict block leads, metric
  cards, why we think this, evidence to submit
- Dispute rate triage threshold set at 0.5% not 0.75% based on
  real merchant data from Shopify community
- Fee math threshold: flag for all disputes under $75
- Stripe fee structure as of June 2025: $15 base, $30 if you
  counter and lose
- VS Code plus terminal is the working environment for Claude Code
- Build sequence: Foundation, Stripe MCP, Delivery MCP, Prompts,
  Evaluator, Frontend, Launch
- Git default branch is main, not master
- Code reviewer agent rule applies to application code only.
  Planning docs and config files can commit without subagent review.
- Hook scripts live in .claude/hooks/ as bash files, referenced from
  .claude/settings.json. JSON tool-input parsing is done in inline
  python for portability. .gitattributes forces LF on .sh so Windows
  CRLF conversion does not break the hooks.
- .claude/settings.local.json (user-specific permissions) is gitignored,
  .claude/settings.json (project-wide config) is committed.

## Known Issues and Blockers

- Auto-update failed on Claude Code install in VS Code terminal.
  Run: npm i -g @anthropic-ai/claude-code to fix when convenient.
  Not a blocker for current phase.
- GitHub CLI (gh) is not installed on this machine. Repo creation
  was done manually via github.com. Install via
  "winget install --id GitHub.cli" if automated repo operations
  are wanted later (not required).

---

## Reference Documents

All in Retina-Advisors project folder:
- CLAUDE.md - working agreement and hard rules
- dispute-analyzer-design-decisions.md - full analytical framework
- retina-advisors-prompt-system.md - all six prompts
- dispute-analyzer-eval-dataset.md - 26 scenarios
- retina-advisors-prompting-skill.md - extension patterns
- Claude_Code_Course_Summary.md - workflow reference

Master planning documents in Fraud Consulting folder:
- pre-build-planning-playbook.md - reusable project methodology
- bryan-voice-style-guide.md - writing voice reference
