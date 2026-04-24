# Retina Advisors - Prompting Skill

Reference document for writing, extending, and modifying prompts in
the Retina Advisors Dispute Analyzer system. Read this before touching
any prompt file in Claude Code.

Last updated: April 23, 2025

---

## The Six-Prompt Architecture

```
STAGE 1 - Parallel (fire simultaneously via asyncio.gather):
  Prompt 2: delivery_fulfillment_analysis  → returns JSON
  Prompt 3: customer_behavior_analysis     → returns JSON
  Prompt 4: transaction_risk_analysis      → returns JSON
  Prompt 5: reason_code_analysis           → returns JSON

STAGE 2 - Sequential:
  Prompt 1: synthesis_prompt               → receives 4 JSON objects,
                                             returns XML report
  Prompt 6: recommendation_quality_evaluator → validates XML report,
                                               returns JSON pass/fail
```

If Prompt 6 returns revision_required, Prompt 1 fires again with
revision instructions appended. Maximum three loops, then escalate
with low confidence flag appended to the report.

All prompts: temperature 0.1, prompt caching on system prompt,
model claude-sonnet-4-20250514.

---

## Prompt Type Standards

### Parallel Prompts (Prompts 2-5)

Parallel prompts have one job: evaluate one evidence stream and
return structured JSON. Nothing else.

Required elements:
- Role definition: narrow, single-purpose. "You are a X evaluator.
  Your only job is to Y and return a structured JSON score."
- Analytical principles: 2-3 rules from the critical rules list
  that apply to this evidence stream specifically. Not all eleven.
- Instructions: what to assess, defined criteria for each assessment,
  exact JSON structure to return.
- Hard output constraint as the final line: "Return a JSON object
  only. No prose. No preamble. No explanation outside the JSON fields."

What parallel prompts must NOT do:
- Make a final recommendation
- Reference other evidence streams
- Produce prose analysis
- Return anything other than the specified JSON structure

**Four rules for writing parallel prompt instructions:**

One - every JSON field value must use a constrained enumeration, not
an open string. Wrong: "assessment": "the delivery looks suspicious."
Right: "fulfillment_score": "strong | moderate | weak". If you cannot
define all possible values in advance, the field should not exist.

Two - every prompt must have a missing_evidence array in its JSON
output. Empty arrays are valid. Never omit it. Missing evidence
affects the synthesis prompt's confidence calculation.

Three - write assessment criteria as decision trees, not descriptions.
Wrong: "assess whether delivery was confirmed." Right: "Strong: confirmed
delivery to billing address with timestamp. Moderate: tracking shows
delivered but address mismatch exists. Weak: no confirmation or
unconfirmed status." Criteria must be mutually exclusive.

Four - the analytical principles in a parallel prompt are behavioral
anchors, not reminders. They must change how the model scores, not
just remind it that context matters. If a principle does not affect
a specific JSON field, it does not belong in this prompt.

### Synthesis Prompt (Prompt 1)

The synthesis prompt has the full role definition, all 11 critical
rules, the input format section explaining the four JSON inputs,
the six-step reasoning process, and the XML output format. It is the
only prompt that produces human-readable output.

Input structure it receives:
```json
{
  "delivery_analysis": {},
  "behavior_analysis": {},
  "transaction_risk": {},
  "reason_code_analysis": {},
  "merchant_context": {
    "dispute_rate": null,
    "risk_posture": "triage | healthy | proactive | unknown",
    "billing_descriptor": null,
    "brand_name": null,
    "mcc": null
  },
  "uploaded_documents": []
}
```

The synthesis prompt follows the recommended_pipeline from
reason_code_analysis. If it overrides that pipeline, it must state
the reason explicitly in the analysis section before proceeding.

### Evaluator Prompt (Prompt 6)

Nine named criteria. Each returns pass, fail, or not_applicable.
The evaluator never modifies the recommendation - only validates
structure, confidence justification, citations, pipeline adherence,
and completeness. Returns JSON only.

---

## XML Output Standards (Synthesis Prompt)

Every report uses these exact tags in this exact order:

```xml
<report>
  <dispute_header>            dispute ID, amount, due date, card network
  <verdict>                   one sentence: recommend + confidence + IS + IS NOT
  <metric_cards>              classification, winnability, dispute_rate_status,
                              confidence
  <reason_code_translation>   one plain English sentence
  <analysis>                  3-5 paragraphs following internal structure
  <evidence_to_submit>        OR
  <acceptance_rationale>      exactly one of these two, never both
  <data_sources_used>         all sources including not_available fields
</report>
```

Tags are validated by the evaluator against criterion 1. A missing
or empty tag fails validation and triggers a revision loop.

Never add or remove XML tags without updating all three:
1. The output_format section of Prompt 1
2. The structure_completeness criterion in Prompt 6
3. The report output structure section in the design decisions document

---

## Voice Standards (Synthesis Output)

These apply to any content written for the synthesis prompt output,
multi-shot examples, and acceptance rationale sections.

Always:
- "this dispute" not "the dispute"
- Active voice: "the evidence shows" not "it can be seen that"
- Name every signal with its source in parentheses immediately after
- State the IS and IS NOT in every verdict
- Frame acceptance as a deliberate strategic decision with a reason

Never:
- "potentially" without a specific qualifier
- More than three sentences without a named signal
- High confidence language with hedging words in the same sentence
- Em dashes anywhere in any prompt or output
- Acceptance framed as resignation or default

Confidence rules:
- High: three or more corroborating signal types named explicitly
- Medium: two corroborating signal types named explicitly
- Low: single signal type or significant data gaps - must name what
  is missing and what would change the assessment
- Never assign High on a single signal regardless of how strong

---

## Common Violations When Extending the System

These are the four rules most frequently broken when adding new
pipelines or modifying existing prompts. Check each one explicitly
before committing any prompt change.

**Violation 1 - Category bias bleeds into new pipelines.**
New pipelines inherit the assumption that the Stripe category name
means what it says. Always add an explicit instruction that the
category is a hypothesis to investigate, not a fact to accept. If
the pipeline does not have a coherence check step, add one.

Check: does the new pipeline's first task treat the category as a
starting point rather than a conclusion?

**Violation 2 - Confidence levels are not justified by signal count.**
When writing new multi-shot examples, the confidence level must be
earned by the number of named corroborating signals, not assigned
based on how the case feels. High confidence examples must explicitly
name three or more signal types. Counting is not optional.

Check: count the named signal types in every example before committing.
High needs three. Medium needs two. Low is anything else.

**Violation 3 - Acceptance rationale sounds like giving up.**
New accept scenarios commonly produce acceptance rationale that reads
as "the evidence is weak so we are accepting." That fails evaluator
criterion 8. Acceptance is always a strategic decision that states
what accepting accomplishes or avoids - preserving processing
relationship, avoiding fee exposure, preventing threshold breach.

Check: does every acceptance rationale contain a positive reason
for accepting, not just a negative reason for not fighting?

**Violation 4 - Refund-in-flight does not surface at the top.**
Rule 9 requires this finding to appear at the TOP of the analysis
section, not in paragraph three. Any new pipeline that touches the
credit_not_processed category must check for refund_in_flight_flag
as its absolute first step before any other analysis.

Check: if refund_in_flight_flag is true in the transaction risk
JSON, does the analysis section open with this finding?

---

## Extension Patterns

### Adding a new pipeline

1. Add a new pipeline entry to the routing step in Prompt 1
   (step id 3) with trigger condition and load-bearing signals
2. Add the pipeline name to the recommended_pipeline enumeration
   in Prompt 5 (reason code analysis)
3. Add eval scenarios covering at minimum: one challenge case with
   high confidence, one accept case, one ambiguous case with low
   confidence
4. Add a load-bearing fields section to the design decisions document
5. Run the full eval dataset after adding - not just the new scenarios

### Adding a new parallel evidence stream

1. Write a new parallel prompt following the parallel prompt
   standards above
2. Add the new JSON output to the input_format section of Prompt 1
3. Add a reference to the new stream in the relevant pipeline
   sections of Prompt 1 step 3
4. Add the new stream to the data_sources_used section of the
   output format in Prompt 1
5. Update asyncio.gather() in the backend to include the new call
6. Add eval scenarios specifically testing the new stream's signals
7. Update the architecture validator subagent checklist

### Adding a new evaluator criterion

1. Add a new criterion block to Prompt 6 with unique id, name,
   pass/fail/not_applicable definition, and specific check logic
2. Add the criterion name to the criteria_results JSON structure
3. Update the failed_criteria array logic
4. If the criterion tests a critical architectural behavior, add it
   to the must-pass list in the eval dataset
5. Re-run all 26 eval scenarios - new criteria can cause previously
   passing scenarios to fail

### Modifying the output structure

Never add or remove XML tags without updating all three documents
listed in the XML output standards section above. Verify the
evaluator criterion 1 reflects the change before testing.

---

## Quality Control - Three Subagents

Three subagents are defined in .claude/agents/ in the project repo.
Run them at the gates specified below. Never skip a gate.

### Subagent 1 - Code Reviewer

**When to run:** Before every commit. Non-negotiable.
**Tools:** Read-only. No file editing.
**Job:** Review the diff since the last commit and flag:
- Implementation bugs and logic errors
- Missing error handling and try/catch blocks
- Broken async patterns (missing await, unhandled promises)
- Incorrect API parameter usage
- Temperature or caching settings that deviate from 0.1 / ephemeral

**Pass condition:** Zero blocking issues flagged. Warnings are noted
but do not block the commit.

### Subagent 2 - Architecture Validator

**When to run:** After each major feature is complete. Required before
the pre-launch eval run.
**Tools:** Read-only.
**Job:** Verify all eight required architecture patterns are actually
implemented in the codebase, not just referenced in comments:

1. Routing - first call classifies and routes, confirm it exists
2. Parallelization - four calls in asyncio.gather(), confirm count
3. Evaluator-optimizer - second call validates, loop exists with
   max three iterations
4. Structured output with citations - XML tags present in output,
   source fields populated in evidence list
5. MCP tool use - Stripe MCP and delivery MCP both connected and
   called
6. Prompt eval pipeline - eval runner exists and is executable
7. Temperature 0.1 - confirmed on all six prompts, not just one
8. Prompt caching - cache_control headers on all six system prompts

**Pass condition:** All eight patterns confirmed present. Any missing
pattern is a launch blocker.

### Subagent 3 - Eval Runner

**When to run:** Before launch. After any prompt change in production.
**Tools:** Read and execute.
**Job:** Run all 26 eval scenarios from the eval dataset against the
live prompt system. Score each scenario pass/fail against three
criteria: correct classification, correct recommendation, correct
confidence level.

**Pass conditions:**
- Must-pass scenarios (1, 2, 8, 12, 13, 16, 20, 26): 8/8 required.
  Any failure here is a launch blocker regardless of overall score.
- Overall score: 23/26 minimum required for launch.

**On failure:** Document which prompt produced the wrong output,
what the specific failure was, and what revision is needed. Re-run
the full dataset after any revision - never re-run only the failed
scenario in isolation.

---

## Prompt Caching Implementation

Add cache_control to every system prompt on every API call:

```python
response = await client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    temperature=0.1,
    system=[
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=messages
)
```

Cache threshold is 1024 tokens. The synthesis prompt easily exceeds
this. All six prompts must be cached from the first API call.
90% cost reduction on cached tokens across every analysis run.

---

## Quality Checklist Before Any Prompt Change

- [ ] Read the full prompt system document before touching anything
- [ ] Identify which of the six prompts the change affects
- [ ] Check whether the change affects the input/output contract
      between stages - parallel JSON structure, synthesis input
      format, evaluator criteria
- [ ] If adding a new pipeline: add eval scenarios first, then
      modify the prompt, not the other way around
- [ ] If modifying XML output structure: update Prompt 1, Prompt 6,
      and the design decisions document in the same session
- [ ] Check against all four common violations listed above
- [ ] Run code reviewer subagent after implementation
- [ ] Run architecture validator if the change touches core patterns
- [ ] Run the full eval dataset - not just affected scenarios
- [ ] Update the design decisions document if the change encodes a
      new analytical principle

---

## File Locations

Prompt system:      Fraud Consulting/retina-advisors-prompt-system.md
Eval dataset:       Fraud Consulting/dispute-analyzer-eval-dataset.md
Design decisions:   Fraud Consulting/dispute-analyzer-design-decisions.md
CLAUDE.md:          project root (also in Fraud Consulting folder)
This skill:         Fraud Consulting/retina-advisors-prompting-skill.md
Subagent files:     .claude/agents/ in project repo
Hook config:        .claude/settings.json in project repo
