## Architecture

Eight patterns. Each one maps to how a fraud analyst thinks.

### 1. Routing

A dedicated Claude call reads the Stripe dispute category and early signals, then routes to the correct analysis pipeline before any evidence evaluation begins.

Fraud analogy: a fraud analyst does not apply the same investigation framework to every transaction. They triage first - is this a card-present dispute, a card-not-present dispute, a friendly fraud pattern? The routing call does the same thing. Classify before you investigate.

Lives in: `src/retina/analyzer.py` - `route_dispute()`

### 2. Parallelization

Four Claude calls fire simultaneously via `asyncio.gather()`, one per evidence stream: delivery and fulfillment, customer behavior, transaction risk, and reason code analysis. Each call is a specialized evaluator with its own prompt and scoring criteria. Results merge into the synthesis prompt only after all four complete.

Fraud analogy: a fraud analyst does not run card network rules first and then run the ML model after. They run both simultaneously and reconcile the outputs. Waiting for one signal before starting the next is how you miss the pattern.

This is not just a parallelization pattern - it is a deterministic design choice. Each evaluator returns structured JSON with explicit scoring. The synthesis prompt receives scored outputs, not raw data. The reasoning is predictable and auditable, not a single opaque call to a large context window.

Lives in: `src/retina/analyzer.py` - `asyncio.gather()` call, four parallel evaluator functions

### 3. Evaluator-Optimizer

After the synthesis prompt produces a recommendation, a second Claude call validates it against nine quality criteria: confidence justification, citation completeness, two-question framework adherence, verdict format, fee math for low AOV disputes, and more. If the recommendation fails any criterion, specific revision instructions feed back to the synthesis prompt. The loop runs up to three times. If it exhausts without approval, the report is flagged with a low confidence warning.

Fraud analogy: a fraud analyst does not deploy a new rule without backtesting it. The evaluator is the backtest - it validates the recommendation against defined criteria before it goes to the merchant. Build, validate, revise. Commit only when it passes.

Lives in: `src/retina/analyzer.py` - `evaluate_and_optimize()`, `src/retina/prompts.py` - `EVALUATOR_PROMPT`

### 4. Structured Output With Citations

The synthesis prompt returns XML. Every factual claim in the analysis section traces to a named source: a Stripe API field, a merchant form input, a delivery MCP result, or an uploaded document. Evidence submitted for challenges includes a source field and a weight rating on every item. The evaluator validates citation completeness on every iteration.

This is how a fraud analyst writes a case file. Every assertion needs a source. "The card fingerprint matches two prior purchases" means nothing without the charge IDs it came from.

Lives in: `src/retina/prompts.py` - `SYNTHESIS_PROMPT` output format, `src/retina/web.py` - `parse_report_xml()`

### 5. MCP Tool Use

Two MCP servers. The Stripe official MCP server pulls dispute data, charge expansions, and customer history. A custom Python MCP server - built for this project - handles delivery status lookups by tracking number and carrier.

The custom server is the meaningful one. Connecting to an existing MCP server demonstrates familiarity with the protocol. Building one demonstrates understanding of how it works. The delivery MCP defines its tools with the `@mcp.tool` decorator, typed parameters, and plain English field descriptions. The SDK generates the schemas Claude needs to call it.

API call discipline: the assembler makes three structured Stripe SDK calls at case intake - dispute object, charge expansion, customer history - assembling a complete data dict before the analysis pipeline fires. The MCP tool use is reserved for the analysis layer, where Claude is making autonomous investigation decisions. Case intake and case investigation are kept separate intentionally.

Lives in: `src/retina/delivery_mcp.py` (custom MCP server), `src/retina/assembler.py` (Stripe SDK calls and MCP lookup)

### 6. Prompt Eval Pipeline

Twenty-six test scenarios covering the full range of dispute types, edge cases, and failure modes. Eight are designated must-pass - scenarios where a wrong recommendation would be materially harmful to a merchant. The eval runner scores each scenario against the evaluator's nine quality criteria. Results are logged with pass/fail per criterion and overall score.

The dataset is fixed. Prompt changes are compared against the same scenarios on every run. This is how you prove a prompt works across the distribution of real inputs, not just the cases you designed it for.

Pre-launch gate: 8/8 must-pass required. 23/26 overall minimum. A must-pass failure blocks launch regardless of overall score.

Lives in: `eval/eval_runner.py`, `eval/grader.py`, `eval/scenarios.py`

### 7. Temperature 0.1

Set on all six prompts from the first API call. Documented in code comments.

Fraud analogy: a rules engine does not give you a different answer on the same transaction twice. A fraud analyst running the same case twice should reach the same classification. Low temperature is the deterministic choice - it trades creative variation for analytical consistency. For a tool making real business recommendations with financial consequences, consistency is not optional.

This is the deterministic versus non-deterministic design decision made explicit. High temperature is appropriate for brainstorming and creative tasks. It is not appropriate for fraud classification.

Lives in: all six prompt calls in `src/retina/analyzer.py` - `temperature=0.1`

### 8. Prompt Caching

`cache_control: ephemeral` on all six system prompts from the first request. The synthesis prompt alone exceeds 1,024 tokens - the minimum threshold for caching. Cached tokens cost 90% less than uncached tokens on the Anthropic API. With six prompts firing on every dispute analysis, caching delivers meaningful cost reduction at any volume.

Fraud analogy: a fraud analyst does not re-read the card network rulebook before every case. The rules do not change between disputes. Cache what does not change, spend cognitive resources on what does.

Lives in: all six prompt calls in `src/retina/analyzer.py` - `cache_control={"type": "ephemeral"}`

---

## Fraud Domain Expertise

The prompts were not written by someone who read about fraud. They encode nine analytical principles drawn from nine years working across card-not-present fraud, card network dispute rules, friendly fraud classification, risk-based decisioning frameworks, and chargeback representment strategy.

A few examples of what that means in practice. Dispute timing is treated as a behavioral fingerprint, not a data point - a dispute filed 97 days after delivery tells a different story than one filed three days after, and the prompts reason about that distinction explicitly. This is the same logic that underpins risk-based decisioning in production fraud systems: the when matters as much as the what.

The coherence test distinguishes true unauthorized fraud (the disputed transaction looks anomalous relative to the cardholder's history - wrong category, wrong amount range, wrong fulfillment pattern) from friendly fraud (the disputed transaction fits the cardholder's history perfectly, because it was the cardholder). Card network rules treat these identically. A fraud analyst does not.

Reason code reliability bias is encoded as a hard rule. Bank reps, not cardholders, often select the reason code. A "no cardholder authorization" code on a transaction with confirmed delivery, a matching card fingerprint, and two prior purchases from the same account is not a fraud case - it is a misapplied code and a winnable dispute. The prompts are instructed to treat the Stripe category as a hypothesis to investigate, not a conclusion to accept.

Friendly fraud gets specific treatment throughout. It was the dominant pattern in DTC disputes before the term was widely used, and it remains the highest-volume misclassified dispute type. Merchants assume "Fraudulent" means a criminal used their customer's card. A large portion of DTC fraudulent disputes are the legitimate cardholder disputing a purchase they made. That distinction is the entire difference between a winnable challenge and an evidence submission that was never going to succeed.

---

## What I Built Versus What I Connected To

The Stripe MCP server is official and maintained by Stripe. Connecting to it is one line of configuration. Building the custom delivery MCP server required defining the tool schema, implementing the lookup logic, writing tests, and connecting it to Claude Code so the analysis pipeline could call it at runtime.

MCP is where agentic fraud tooling is heading. The most sophisticated chargeback platforms in the market are now launching MCP servers as product features - so their intelligence can be queried by AI agents the way a data warehouse is queried by analysts. Building at that layer now, rather than consuming it, is the relevant skill.

---

## Eval Pipeline

Twenty-six scenarios. Eight must-pass. Scored against nine criteria, not eyeballed against cherry-picked examples.

A demo that works once is not the same as a system that works reliably. The eval pipeline is how you tell the difference. Every prompt change is compared against the same fixed dataset. Win rates are calculated, not asserted.

Current status: 8/8 must-pass confirmed. Full 26-scenario run pending final cost optimization.

---

## Tech Stack

- Backend: Python, FastAPI, Jinja2
- Frontend: Tailwind CSS, HTMX
- AI: Anthropic API - claude-sonnet-4-6, six prompts, asyncio
- MCP: Stripe official MCP server, custom Python delivery MCP server
- Payments: Stripe Python SDK
- Tests: pytest, 43 passing
- Deployed: www.retinaadvisors.com

---

## V2 Roadmap

- Shopify MCP integration - pull order and fulfillment data directly from Shopify alongside Stripe, closing the gap on merchants who do not use Stripe for fulfillment tracking
- Auto-calculated dispute rate from Stripe charge history - remove the self-reported field, calculate the rate directly from the merchant's actual data
- Email and communication thread analysis - detect pre-dispute merchant contact patterns from uploaded email threads without manual field entry
- Aggregated pattern analysis across dispute history - surface repeat offenders, clustering by card fingerprint, shipping address, and dispute reason across multiple disputes
- Stripe Radar rule recommendations - translate dispute classification findings into concrete Radar rule suggestions the merchant can implement immediately

---

## Built With

Built with Claude Code.

Source: github.com/bshap18-sys/Retina-Advisors
