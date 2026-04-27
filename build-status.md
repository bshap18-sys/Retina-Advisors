# Retina Advisors - Build Status

Update this file at the end of every session. A new chat session
reads this first to know exactly where the project stands.

Last updated: April 27, 2025 (Phase 3 complete)
Current phase: Phase 4 - Prompt System Implementation

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
Status: COMPLETE
Started: April 25, 2025
Completed: April 25, 2025
Tasks:
- [x] Stripe MCP server added to Claude Code
- [x] Test pull of dispute object confirmed
- [x] Test pull of charge object expansion confirmed
- [x] Test pull of customer history confirmed (schema validated against API reference; live multi-call query deferred to Phase 4 since the first test charge had no linked customer object)
- [x] Data layer validated before building on top of it
Notes: Stripe official MCP server is connected via .mcp.json with
STRIPE_API_KEY loaded from .env. End-to-end probe confirmed
(retrieve_balance, list_disputes, fetch_stripe_resources). A test
dispute was created against test card 4000 0000 0000 0259 and
pulled back through the MCP. Field-level validation of the design's
input form against the canonical Stripe API reference produced
dispute-analyzer-stripe-field-map.md, which closes the pre-code
gate item "Stripe MCP field research." Critical finding: customer
name, email, billing address, and purchase IP do not live on the
dispute object as ground truth - they are merchant-supplied
evidence slots there - so the design was corrected to pull them
from the charge object's billing_details. All four pre-code gates
are now satisfied; we are clear to write Python.

Phase 3 - Custom Delivery MCP Server
Status: COMPLETE
Completed: April 27, 2025
Commit: c7c7b2f
Tasks:
- [x] Python MCP server file created
- [x] Delivery status lookup tool defined
- [x] Server tested locally
- [x] Server connected to Claude Code
- [x] Test lookup confirmed working
Notes: Custom delivery MCP server built in Python. 9 tests passing,
verified live end-to-end. Demonstrates Bryan can build MCP servers,
not just connect to existing ones. Portfolio critical - confirmed.

Phase 4 - Prompt System Implementation
Status: IN PROGRESS
Started: April 27, 2025
Tasks:
- [x] Python async architecture scaffolded
- [x] All six prompts loaded from prompt system document (plus routing = 7 total)
- [x] Temperature 0.1 set on all six prompts
- [x] Prompt caching headers added to all six
- [x] asyncio.gather() wiring all four parallel calls
- [x] Synthesis prompt receiving four JSON inputs correctly
- [x] Evaluator prompt connected to synthesis output
- [ ] Scenario 1 from eval dataset run successfully (requires live API key in shell)
Notes: Three new files written: src/retina/prompts.py (7 prompt constants),
src/retina/analyzer.py (7-call pipeline), tests/test_analyzer.py (5 unit
tests + 1 integration test). All 15 non-integration tests pass, zero
regressions. Code reviewer approved with zero blocking issues.
MODEL corrected to claude-sonnet-4-6 (prompt system doc had
claude-sonnet-4-20250514, a date that was in the future when the doc was
written and is not a valid current model ID).
Routing prompt written fresh - it did not exist in retina-advisors-prompt-system.md.

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

April 25, 2025:
- Pre-code gate fully closed. Field-level validation of the design's
  input form against the canonical Stripe API reference (Dispute and
  Charge objects) produced dispute-analyzer-stripe-field-map.md.
- Critical correction applied to design-decisions.md: customer name,
  email, billing address, and purchase IP moved from Layer 1 (dispute
  object) to Layer 2 (charge object). They were sitting on
  dispute.evidence.* in the design, which is a merchant-supplied
  evidence slot, not Stripe ground truth.
- First test dispute created via test card 4000 0000 0000 0259,
  pulled back through Stripe MCP, full field schema verified against
  docs.stripe.com/api/disputes/object and /api/charges/object.
- Confirmed: fraudulent is the canonical first-test pipeline.
  Highest DTC volume, exercises all four parallel evidence streams.
  Other reason codes are easier and will follow.
- Stripe MCP behavior observation: list_disputes and
  fetch_stripe_resources return slim summaries by design (context
  economy). The MCP is the right tool for runtime use by the
  analyzer, not for design-time schema enumeration. The published
  API reference is the canonical source for field schemas.

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
