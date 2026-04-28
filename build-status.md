# Retina Advisors - Build Status

Update this file at the end of every session. A new chat session
reads this first to know exactly where the project stands.

Last updated: April 28, 2026
Current phase: Phase 6 - Input Form and Frontend

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
- [x] Test pull of customer history confirmed (schema validated against
      API reference; live multi-call query deferred to Phase 4 since
      the first test charge had no linked customer object)
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
Status: COMPLETE
Started: April 27, 2025
Completed: April 28, 2025
Commit: 5e03203
Tasks:
- [x] Python async architecture scaffolded
- [x] All six prompts loaded from prompt system document
      (plus routing = 7 total)
- [x] Temperature 0.1 set on all six prompts
- [x] Prompt caching headers added to all six
- [x] asyncio.gather() wiring all four parallel calls
- [x] Synthesis prompt receiving four JSON inputs correctly
- [x] Evaluator prompt connected to synthesis output
- [x] Scenario 1 from eval dataset run successfully
      (integration test passing)
Notes: Three new files written: src/retina/prompts.py (7 prompt
constants), src/retina/analyzer.py (7-call pipeline),
tests/test_analyzer.py (5 unit tests + 1 integration test).
All 15 non-integration tests pass, zero regressions. Code reviewer
approved with zero blocking issues.
MODEL corrected to claude-sonnet-4-6 (prompt system doc had
claude-sonnet-4-20250514, a date that was in the future when the
doc was written and is not a valid current model ID).
Routing prompt written fresh - it did not exist in
retina-advisors-prompt-system.md.
Bug fixed end of phase: Claude wraps JSON responses in markdown code
fences despite no-preamble instructions. Added fence stripping in
_call_claude before returning - strips leading ```json, leading ```,
and trailing ```.
Evaluator-optimizer loop also fully coded in this phase
(see Phase 5 notes).

Phase 5 - Evaluator Loop
Status: COMPLETE
Started: April 28, 2025
Completed: April 28, 2025
Commit: 5fe125b
Tasks:
- [x] Evaluator fires after synthesis prompt
- [x] Revision loop wired with maximum three iterations
- [x] Escalation with low confidence flag on loop timeout
- [x] Scenario 26 (evaluator loop test) passes
Notes: The loop code was written as part of Phase 4 (analyze_dispute
lines 369-386 in analyzer.py). MAX_EVALUATOR_LOOPS=3, revision
instructions fed back to synthesize() on each failed iteration,
low_confidence_flag appended as an XML comment when the loop
exhausts without approval. Scenario 26 confirmed live: evaluator
correctly caught all five required failing criteria
(confidence_justification, two_question_framework,
citation_completeness, verdict_format, no_false_confidence) on the
deliberately weak four-sentence input and returned revision_required
with specific revision instructions.

Phase 6 - Input Form and Frontend
Status: IN PROGRESS
Sub-phases: 6A (Scaffolding) COMPLETE, 6B (Assembler), 6C (Form),
            6D (Report Renderer), 6E (End to End)

Stack decisions locked April 28, 2026:
- Framework: FastAPI + Jinja2 templates
- Styling: Tailwind CSS via CDN (no build toolchain)
- Async UX: HTMX via CDN (async form submit, loading state swap)
- Stripe data: Stripe Python SDK in assembler.py (not Stripe MCP)
  Rationale: assembler is case intake, not autonomous Claude
  investigation. SDK for pulling known dispute data. MCP remains
  in Claude analysis calls.
- Document uploads: in Phase 6, pre-processed in assembler via a
  separate Claude API call before pipeline fires. Returns
  document_type and key_findings JSON. Pipeline receives
  pre-processed findings not raw files.
- File structure: all new files inside src/retina/ alongside
  existing code
- Loading state: HTMX simple swap pattern. Progressive rendering
  (streaming parallel results as they complete) deferred to v2.
- analyzer.py and prompts.py: NO changes in Phase 6 - pipeline is
  complete and tested, assembler feeds it a finished dict

---

## Phase 6 Task Breakdown

### Phase 6A - Scaffolding
Status: COMPLETE
Commit: (this session)

Tasks:
- [x] Install dependencies: fastapi, uvicorn, jinja2, stripe,
      python-multipart. Add all to requirements.txt.
- [x] Create src/retina/web.py - FastAPI app instance, single GET
      route for "/" that renders form.html template
- [x] Create src/retina/templates/ directory
- [x] Create src/retina/templates/base.html - base Jinja2 template:
      Tailwind CSS loaded from CDN
      HTMX loaded from CDN
      Page title "Retina Advisors - Dispute Analyzer"
      Navigation bar with Retina Advisors branding
      Content block for child templates
- [x] Create src/retina/templates/form.html - extends base.html,
      renders empty form placeholder (no fields yet)
- [x] Create src/retina/templates/report.html - extends base.html,
      renders empty report placeholder (no structure yet)
- [x] Add uvicorn start command to key commands section:
      uvicorn src.retina.web:app --reload
- [x] Verify: uvicorn starts, browser loads at localhost:8000,
      Tailwind styles visible, no console errors
- [x] Run code reviewer subagent before commit
- [x] Commit: "Phase 6A - FastAPI scaffolding, base templates,
      Tailwind + HTMX"
Notes: Zero blocking issues from code reviewer. 10 existing tests
pass, zero regressions. Tailwind CDN is unpinned (intentional for
scaffolding) - pin before production. HTMX pinned to 1.9.12.
stripe package installed here though first used in Phase 6B.

---

### Phase 6B - Assembler
Goal: assembler.py pulls real Stripe data for a dispute ID,
combines it with form inputs and uploaded document findings,
returns a complete dict that analyze_dispute() accepts without
modification. Tested directly against sandbox dispute ID before
any form exists.

The assembler is the data assembly layer. It does NOT call
analyze_dispute(). It returns a dict. The web route calls
analyze_dispute() with that dict.

Tasks:

Stripe SDK setup:
- [ ] Confirm stripe Python package installed (added in 6A)
- [ ] Confirm STRIPE_API_KEY loading from .env in web.py
      (key already in .env from Phase 2 - confirm present)
- [ ] Verify stripe.Dispute.retrieve() works against sandbox
      dispute ID before building anything else

assembler.py - core structure:
- [ ] Create src/retina/assembler.py
- [ ] Define assemble_dispute_input(dispute_id, form_data,
      documents) function - takes dispute ID string, form_data
      dict from form submission, documents list of uploaded
      file bytes
- [ ] Stripe Call 1 - dispute object:
      stripe.Dispute.retrieve(dispute_id,
      expand=["charge", "charge.customer"])
      Pulls: reason code, category, amount, currency,
      evidence_due_by, status
- [ ] Stripe Call 2 - charge expansion:
      From expanded charge object extract:
      ECI indicator, wallet type, AVS result, CVC result,
      3DS outcome, card brand, funding type, network transaction
      ID, Radar risk score, Radar risk level, Radar rule fired,
      metadata (order ID, product info), refund history with
      timestamps.
      All field names must match dispute-analyzer-stripe-field-map.md
- [ ] Stripe Call 3 - customer history:
      Using card fingerprint from charge object, query
      stripe.Charge.list() filtered by card fingerprint to build
      prior transaction count, prior dispute count, order velocity
- [ ] Delivery MCP lookup:
      Call get_delivery_status() from delivery_mcp.py using
      tracking number and carrier from form_data if provided.
      Import and call directly - delivery MCP is local Python,
      no HTTP call needed.
- [ ] Document pre-processing:
      If documents list is not empty, make a separate Claude API
      call for each uploaded file. Pass base64-encoded file as
      image or document block. System prompt instructs Claude to
      extract key findings relevant to a payment dispute and
      return JSON with document_type and key_findings fields.
      Temperature 0.1. This call is NOT part of the main pipeline -
      it runs in the assembler before analyze_dispute() is called.
- [ ] Assemble and return complete dispute_input dict matching the
      exact structure analyze_dispute() expects. Every field name
      must match what the prompts reference. See
      dispute-analyzer-design-decisions.md data architecture
      section for the six layers.
- [ ] Handle missing fields gracefully - use None for unavailable
      data, never omit keys the prompts reference

assembler.py - error handling:
- [ ] Wrap Stripe calls in try/except - if dispute ID not found,
      raise clear ValueError with user-facing message
- [ ] If charge expansion fails, log warning and continue with
      available data - do not block analysis
- [ ] If delivery MCP lookup fails, set delivery fields to None
      and log warning - do not block analysis
- [ ] If document pre-processing Claude call fails, log warning
      and continue with empty uploaded_documents list - do not
      block analysis

assembler.py - tests:
- [ ] Create tests/test_assembler.py
- [ ] Unit test: assemble_dispute_input with sandbox dispute ID
      returns dict with all required top-level keys present
- [ ] Unit test: Stripe dispute fields correctly mapped - spot
      check at minimum reason_code, amount, category,
      evidence_due_by
- [ ] Unit test: charge expansion fields correctly mapped - spot
      check at minimum eci_indicator, radar_score, avs_result,
      refund history
- [ ] Unit test: missing form fields produce None values not
      KeyError
- [ ] Unit test: invalid dispute ID raises ValueError with
      clear message
- [ ] Integration test (marked, requires STRIPE_API_KEY): full
      assemble call against sandbox dispute ID returns populated
      dict
- [ ] All tests passing before moving to 6C
- [ ] Run code reviewer subagent before commit
- [ ] Commit: "Phase 6B - assembler.py, Stripe SDK integration,
      document pre-processing, assembler tests"

---

### Phase 6C - Form Build
Goal: Full merchant input form rendered in browser, Tailwind
styled, HTMX wired for async submit with loading state. On
submit, form calls assembler then analyze_dispute and returns
rendered report. All five field groups plus document upload
section present.

Tasks:

FastAPI POST route:
- [ ] Add POST route "/analyze" to web.py
      Accepts: dispute_id (str), all form fields (Form params),
      uploaded files (UploadFile list via python-multipart)
      Calls assembler.assemble_dispute_input()
      Calls analyzer.analyze_dispute() with assembled dict
      Returns rendered report.html with analysis result
- [ ] HTMX swap pattern: form div replaced by loading div on
      submit, loading div replaced by report div on response
- [ ] Error route: if assembler raises ValueError (bad dispute
      ID), render form again with inline error message

Form fields - form.html:
All fields from design decisions doc data architecture Layer 5.
Every field below is load-bearing - produces genuinely different
recommendation output.

Dispute lookup section (top of form):
- [ ] Dispute ID (text input, required)
      Helper: "Find in Stripe Dashboard under Radar > Disputes.
      Starts with dp_"

Merchant context section:
- [ ] Current dispute rate (number input, optional, step=0.01)
      Placeholder: "e.g. 0.3 for 0.3%"
      Helper: "Find in Stripe Analytics. Leave blank if unknown."
- [ ] MCC (text input, optional)
      Helper: "Find in Stripe Dashboard under Business settings"
- [ ] Risk posture (select: triage / healthy / proactive /
      unknown). Default: unknown
- [ ] Billing descriptor (text input, optional)
      Helper: "Exactly what appears on your customer's card
      statement - not your brand name"

Fulfillment data section:
- [ ] Tracking number (text input, optional)
- [ ] Carrier (select: UPS / FedEx / USPS / DHL / Other /
      Unknown)
- [ ] Ship date (date input, optional)
- [ ] Delivery date (date input, optional)
- [ ] Delivery confirmation status (select: confirmed /
      unconfirmed / failed / unknown)
- [ ] Billing address matched shipping address (select: yes /
      no / unknown)

Customer contact section:
- [ ] Did customer contact merchant before filing dispute?
      (select: yes / no / unknown)
- [ ] Did merchant contact customer before dispute?
      (select: yes / no / unknown)
- [ ] Notes from customer contact exchange (textarea, optional)
      Placeholder: "Paste relevant email excerpts or call notes"

Order context section:
- [ ] Product type (select: physical goods / digital download /
      subscription / service)
- [ ] Confirmation email sent (select: yes - available to submit
      / yes - not available / no)

Policy section:
- [ ] Refund/return policy exists (select: yes / no)
- [ ] Policy shown at checkout (select: yes / no / unknown)

Document upload section:
- [ ] File upload input (multiple files accepted)
      Accepted types: PDF, PNG, JPG, JPEG
      Helper: "Upload delivery confirmation photos, customer
      email screenshots, product photos, or other evidence.
      Claude will read and extract key findings from each file."
- [ ] Display selected file names before submit

Form UX and styling:
- [ ] Section headers with clear visual separation between the
      six field groups
- [ ] Required fields marked with asterisk
- [ ] Submit button: "Analyze Dispute" - prominent, full-width
      on mobile
- [ ] HTMX on form: hx-post="/analyze"
      hx-target="#result-container" hx-swap="innerHTML"
      hx-indicator="#loading-indicator"
- [ ] Loading div (#loading-indicator): hidden by default,
      shown during request. Content: Tailwind animate-spin
      spinner + "Analyzing dispute... this takes 20-30 seconds"
- [ ] Result container div (#result-container): empty on load,
      HTMX swaps report HTML in when analysis completes
- [ ] Form validation: dispute ID required, all other fields
      optional with helper text on load-bearing fields

Form tests:
- [ ] Manual: form loads at localhost:8000 with no errors
- [ ] Manual: all six sections visible and correctly labeled
- [ ] Manual: submit with dispute ID only - loading state appears
- [ ] Manual: invalid dispute ID - error renders inline, no
      page reload
- [ ] Run code reviewer subagent before commit
- [ ] Commit: "Phase 6C - form build, all field groups, HTMX
      async submit, loading state, document upload"

---

### Phase 6D - Report Renderer
Goal: XML output from synthesis prompt parsed and rendered as
professional HTML report. Verdict block with green/red left
border, four metric cards, structured analysis, prioritized
evidence list with citations, data sources footer.

Tasks:

XML parsing in web.py:
- [ ] Write parse_report_xml(xml_string) in web.py
      Extracts all required XML tags using xml.etree.ElementTree
      with string parsing fallback
      Returns dict with keys: dispute_header, verdict,
      metric_cards, reason_code_translation, analysis,
      evidence_to_submit (or None), acceptance_rationale
      (or None), data_sources_used
- [ ] Parse metric_cards into individual fields:
      classification, winnability, dispute_rate_status,
      confidence
- [ ] Parse evidence_to_submit into list of items each with:
      number, description, source, weight
- [ ] Handle malformed/incomplete XML gracefully - missing tag
      returns None placeholder, no crash

report.html - structure and Tailwind styling:
- [ ] Dispute header bar (full width, top of report):
      Dispute ID, amount, evidence due date, card network
      Dark background, white text, monospace font for dispute ID
- [ ] Verdict block (prominent, below header):
      Green left border (border-l-4 border-green-500) for
      Challenge. Red (border-red-500) for Accept.
      Large bold verdict text - one sentence.
      Confidence badge: pill shape, color-coded green/yellow/red
      for High/Medium/Low
- [ ] Metric cards row (four cards, responsive):
      Card 1: Classification
      Card 2: Winnability (color-coded Strong/Moderate/Weak)
      Card 3: Dispute Rate Status (color-coded by threshold)
      Card 4: Confidence Level (color-coded)
      Each card: icon, label, value, clean border, subtle shadow
      Mobile: 2x2 grid
- [ ] Reason code translation (below metric cards):
      Light background, italic text
      If misapplication flag: amber warning banner above
      ("Note: this reason code may not match the evidence")
- [ ] Analysis section:
      Readable typography, generous line height
      Named signal citations in distinct style (monospace or
      small caps for source names in parentheses)
- [ ] Evidence to submit (if challenging):
      Numbered list with visual hierarchy
      Primary weight: bold and prominent
      Supporting weight: normal
      Supplementary weight: muted
      Each item: what it proves, source, weight badge
- [ ] Acceptance rationale (if accepting):
      Amber/yellow tonal background - signals strategic accept,
      not a failure or default
- [ ] Data sources section (collapsible footer):
      CSS details/summary element - no JS needed
      All six data source categories, available and missing
- [ ] Print hint: small "Save as PDF" note (browser print handles
      PDF export, no extra library)
- [ ] Retina Advisors branding footer

report.html - responsive:
- [ ] Full report readable on mobile, no horizontal scroll
- [ ] Metric cards 2x2 on small screens
- [ ] Nav bar collapses on mobile

Report renderer tests:
- [ ] Unit test: parse_report_xml with valid XML returns dict
      with all expected keys populated
- [ ] Unit test: parse_report_xml with missing evidence_to_submit
      tag returns None for that key, no exception
- [ ] Unit test: parse_report_xml with malformed XML returns
      graceful fallback dict, no crash
- [ ] Manual: rendered report with Scenario 1 output looks
      correct - all sections visible, colors correct
- [ ] Run code reviewer subagent before commit
- [ ] Commit: "Phase 6D - report renderer, XML parsing, Tailwind
      report template, metric cards, verdict block"

---

### Phase 6E - End to End
Goal: Full dispute analysis flow working from browser to browser.
Real dispute ID, real Stripe data, real pipeline, real report.
Fix whatever breaks.

Tasks:
- [ ] Full end-to-end test with sandbox dispute ID:
      1. Start uvicorn dev server
      2. Open localhost:8000
      3. Enter sandbox dispute ID
      4. Fill in representative form fields
      5. Submit form
      6. Verify HTMX loading state appears immediately
      7. Verify report renders after pipeline completes
      8. Verify all report sections populated correctly
      9. Verify no console errors, no 500s in uvicorn logs
- [ ] Edge case tests:
      - Submit with only dispute ID, all optional fields empty
      - Submit with invalid dispute ID - clean error message
      - Upload a PDF - verify pre-processing runs and findings
        appear in data_sources_used
      - Upload an image - same verification
- [ ] Fix any XML parsing issues from real pipeline output
- [ ] Fix any assembler field mapping issues discovered
- [ ] Fix any Tailwind styling issues from real report content
- [ ] Run pytest - confirm all 15+ existing tests still passing,
      zero regressions
- [ ] Run code reviewer subagent
- [ ] Run architecture validator subagent - all eight patterns
      confirmed present after Phase 6 additions
- [ ] Commit: "Phase 6E - end to end verified, full analysis
      flow working browser to browser"

---

## New files added in Phase 6

src/retina/web.py             - FastAPI app, GET/POST routes,
                                XML parsing, template rendering
src/retina/assembler.py       - Stripe SDK calls, delivery MCP
                                lookup, document pre-processing,
                                dict assembly
src/retina/templates/
  base.html                   - base Jinja2 template with
                                Tailwind + HTMX from CDN
  form.html                   - dispute input form, all field
                                groups, HTMX wiring
  report.html                 - rendered analysis report,
                                verdict block, metric cards
tests/test_assembler.py       - assembler unit and integration
                                tests

Do NOT modify in Phase 6:
  src/retina/analyzer.py      - pipeline complete, frozen
  src/retina/prompts.py       - prompts complete, frozen
  src/retina/delivery_mcp.py  - MCP server complete, frozen
  tests/test_analyzer.py      - existing tests must stay green

---

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

## Environment Setup

Python: 3.14.0 at C:\Python314\python.exe
Venv: .venv in project root (gitignored)
Key commands:
  Activate venv: .venv\Scripts\activate
  Run tests: pytest
  Start dev server: uvicorn src.retina.web:app --reload
  Integration tests: set ANTHROPIC_API_KEY=... in separate terminal
    .venv\Scripts\python.exe -m pytest tests/test_analyzer.py -k
    "scenario_1" -v -s
    .venv\Scripts\python.exe -m pytest tests/test_analyzer.py -k
    "scenario_26" -v -s
  Assembler integration test: set STRIPE_API_KEY=... then
    .venv\Scripts\python.exe -m pytest tests/test_assembler.py -k
    "integration" -v -s

Secrets:
  STRIPE_API_KEY - in .env, never committed
  ANTHROPIC_API_KEY - in .env, never committed, created April 27 2026
  Note: Set manually in separate terminal for integration tests

---

## Key Decisions Made

April 28, 2026 - Phase 6 planning:
- FastAPI + Jinja2 + Tailwind CSS CDN + HTMX CDN selected
- Stripe Python SDK used in assembler for data assembly (not Stripe
  MCP). Assembler is case intake, not autonomous investigation.
- Document uploads pre-processed in assembler via separate Claude
  API call before analyze_dispute() fires. Zero changes to tested
  pipeline.
- All Phase 6 files in src/retina/ - no separate web/ directory.
- HTMX simple swap for loading state. Progressive rendering = v2.
- analyzer.py and prompts.py frozen for Phase 6.

April 25, 2025:
- Pre-code gate fully closed. Field-level validation of the design's
  input form against the canonical Stripe API reference produced
  dispute-analyzer-stripe-field-map.md.
- Critical correction: customer name, email, billing address, and
  purchase IP moved from Layer 1 (dispute object) to Layer 2
  (charge object). They were sitting on dispute.evidence.* which
  is a merchant-supplied evidence slot, not Stripe ground truth.
- First test dispute created via test card 4000 0000 0000 0259,
  pulled back through Stripe MCP, full field schema verified.
- Stripe MCP behavior: list_disputes and fetch_stripe_resources
  return slim summaries by design. MCP is the right tool for
  runtime use by the analyzer, not design-time schema enumeration.

April 24, 2025:
- Six-prompt architecture finalized
- 26 eval scenarios built with must-pass designations
- Output format: Option B hybrid - verdict block leads, metric
  cards, why we think this, evidence to submit
- Dispute rate triage threshold: 0.5% not 0.75% based on real
  merchant data from Shopify community
- Fee math threshold: flag for all disputes under $75
- Stripe fee structure as of June 2025: $15 base, $30 if counter
  and lose
- VS Code plus terminal is the working environment for Claude Code
- Git default branch is main, not master
- Code reviewer agent rule applies to application code only.
  Planning docs and config files can commit without review.
- Hook scripts live in .claude/hooks/ as bash files. JSON input
  parsed with inline python for portability. .gitattributes forces
  LF on .sh so Windows CRLF does not break hooks.
- .claude/settings.local.json gitignored,
  .claude/settings.json committed.

---

## Known Issues and Blockers

None currently blocking. Clean working tree on main.

Non-blocking notes carried forward:
- Auto-update failed on Claude Code install in VS Code terminal.
  Run: npm i -g @anthropic-ai/claude-code to fix when convenient.
- GitHub CLI (gh) not installed. Repo creation was done manually.
  Install via winget install --id GitHub.cli if needed later.
- No xml fence branch in _call_claude (low priority)
- dispute_input["_routing"] mutation is documented design choice
- INTRANSIT naming slightly inconsistent with hyphenated convention

---

## Reference Documents

All in Retina-Advisors project folder:
- CLAUDE.md - working agreement and hard rules
- dispute-analyzer-design-decisions.md - full analytical framework
- retina-advisors-prompt-system.md - all six prompts
- dispute-analyzer-eval-dataset.md - 26 scenarios
- retina-advisors-prompting-skill.md - extension patterns
- dispute-analyzer-stripe-field-map.md - Stripe field-to-API mapping
- Claude_Code_Course_Summary.md - workflow reference

Master planning documents in Fraud Consulting folder:
- pre-build-planning-playbook.md - reusable project methodology
- bryan-voice-style-guide.md - writing voice reference

GitHub: https://github.com/bshap18-sys/Retina-Advisors
