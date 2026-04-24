# Retina Advisors Dispute Analyzer - Eval Dataset

26 dispute scenarios covering every fraud type, edge case, and merchant
situation the prompt system must handle. Each scenario has a defined
input set and expected output. Use this dataset to score the tool
before launch and after any prompt changes.

Last updated: April 23, 2025

---

## SCORING RULES

### Pass/Fail Criteria
Each scenario is scored pass or fail against three criteria:
1. Correct classification
2. Correct recommendation (challenge or accept)
3. Correct confidence level (high, medium, or low)

All three must match the expected output for a pass.

### Acceptable Variance
Some scenarios have genuinely ambiguous inputs. For these, an
alternative classification is acceptable if the recommendation
and confidence level are still correct. Acceptable alternatives
are noted per scenario.

### Must-Pass Scenarios
These scenarios have zero tolerance for failure. They test the
most critical architectural behaviors and highest-value fraud
patterns. A launch-blocking failure is any must-pass scenario
that fails.

Must-pass: 1, 2, 8, 12, 13, 16, 20, 26

### Acceptable Failure Scenarios
These scenarios involve genuine ambiguity. A single failure here
does not block launch if the tool's reasoning is sound.

Acceptable variance: 15, 21, 24

### Target Score
Minimum before launch: 23/26 (88%)
Must-pass scenarios: 8/8 (100%) - no exceptions

---

## SCENARIO 1 - MUST PASS
### Friendly Fraud - High Confidence - Dispute
Source: Design session analytical principles

Input:
- Category: Fraudulent
- Reason code: Visa 10.4
- Amount: $284.00
- Dispute rate: 0.3% - healthy
- ECI: 05 (full 3DS)
- Wallet: Apple Pay
- AVS: Y - full match
- CVC: M - match
- Radar score: 12
- Prior orders on fingerprint: 2
- Prior disputes: 0
- Days to dispute: 47
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Product type: physical goods

Expected output:
- Classification: Friendly fraud
- Recommendation: Challenge
- Confidence: High
- Winnability: Strong
- Key signals cited: 3DS authentication, confirmed delivery, prior
  purchase history, no pre-dispute contact, timeline

Acceptable variance: none - this is the clearest friendly fraud
scenario in the dataset. All three criteria must match exactly.

---

## SCENARIO 2 - MUST PASS
### Friendly Fraud - Calculated Timeline - Dispute
Source: Timeline fingerprint principle - 90+ day pattern

Input:
- Category: Fraudulent
- Reason code: Mastercard 4837
- Amount: $156.00
- Dispute rate: 0.4% - healthy
- ECI: 05
- Wallet: standard card entry
- AVS: Y
- CVC: M
- Radar score: 18
- Prior orders on fingerprint: 3
- Prior disputes: 0
- Days to dispute: 103
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Product type: physical goods

Expected output:
- Classification: Friendly fraud
- Recommendation: Challenge
- Confidence: High
- Winnability: Strong
- Key finding: 103-day timeline must be flagged as calculated
  behavior - true fraud victims dispute immediately. This signal
  must appear explicitly in the analysis.

Acceptable variance: none - the 103-day timeline is the defining
signal and must be identified and named.

---

## SCENARIO 3
### True Unauthorized - Accept
Source: Design session coherence test, research on card compromise patterns

Input:
- Category: Fraudulent
- Reason code: Mastercard 4837
- Amount: $312.00
- Dispute rate: 0.6% - triage
- ECI: 07 (no 3DS)
- Wallet: standard card entry
- AVS: N - no match
- CVC: M
- Radar score: 81
- Prior orders on fingerprint: 0
- Prior disputes: 0
- Days to dispute: 2
- Delivery: delivered to address different from billing
- Shipping address type: freight forwarder
- Pre-dispute customer contact: none
- Product type: physical goods

Expected output:
- Classification: True unauthorized
- Recommendation: Accept
- Confidence: Medium
- Winnability: Weak
- Key signals: no prior history, AVS failure, no 3DS, delivery to
  freight forwarder, filed within 2 days, Radar 81
- Triage mode noted as additional reason to accept

Acceptable variance: confidence level can be High instead of Medium
if tool cites four or more corroborating signals. All other
criteria must match exactly.

---

## SCENARIO 4
### Product Not Received - Legitimate - Accept
Source: Shopify community thread - merchant lost despite tracking evidence

Input:
- Category: Product Not Received
- Reason code: Visa 13.1
- Amount: $89.00
- Dispute rate: 0.5% - caution
- ECI: 07
- AVS: Y
- CVC: M
- Radar score: 22
- Prior orders on fingerprint: 1
- Prior disputes: 0
- Days to dispute: 14
- Delivery: unconfirmed - tracking shows in transit, not delivered
- Billing/shipping address match: yes
- Pre-dispute customer contact: customer emailed merchant twice
  before disputing
- Product type: physical goods
- Confirmation email: sent, not available to submit

Expected output:
- Classification: Genuine fulfillment failure
- Recommendation: Accept
- Confidence: Medium
- Winnability: Weak - no delivery confirmation is fatal to this case
- Key finding: customer contacted merchant before disputing -
  charitable default applies, this appears legitimate
- Note: merchant should resolve carrier issue

Acceptable variance: classification can be Ambiguous instead of
Genuine fulfillment failure if tool notes competing hypotheses.
Recommendation and confidence must still match exactly.

---

## SCENARIO 5
### Product Not Received - Friendly Fraud Pattern - Dispute
Source: Design session - PNR as friendly fraud vector

Input:
- Category: Product Not Received
- Reason code: Visa 13.1
- Amount: $198.00
- Dispute rate: 0.3% - healthy
- ECI: 06
- AVS: Y
- CVC: M
- Radar score: 31
- Prior orders on fingerprint: 4
- Prior disputes: 0
- Days to dispute: 8
- Delivery: confirmed to billing address 6 days before dispute
- Billing/shipping address match: yes
- Pre-dispute customer contact: none
- Product type: physical goods
- Confirmation email: sent, available to submit

Expected output:
- Classification: Friendly fraud
- Recommendation: Challenge
- Confidence: High
- Winnability: Strong
- Key finding: delivery confirmed 6 days before dispute with no
  merchant contact before filing. Must note this does not match
  legitimate item not received behavior.

Acceptable variance: none.

---

## SCENARIO 6
### Subscription Canceled - Winnable - Dispute
Source: Research - subscription confusion is third most common dispute type

Input:
- Category: Subscription Canceled
- Reason code: Visa 13.6
- Amount: $79.00
- Dispute rate: 0.2% - healthy
- ECI: not applicable - recurring billing
- AVS: not applicable - recurring billing
- CVC: not applicable - recurring billing
- Radar score: 21
- Prior orders on fingerprint: 8
- Prior disputes: 0
- Days to dispute: 21
- Pre-dispute customer contact: none
- Confirmation email: sent with cancellation terms, available to submit
- Return/cancellation policy shown at signup: yes
- Product type: subscription

Expected output:
- Classification: Subscription misunderstanding
- Recommendation: Challenge
- Confidence: Medium
- Winnability: Moderate - cancellation terms in confirmation email
  is the load-bearing evidence
- Key finding: 8 prior billing cycles with no dispute suggests
  customer understood the subscription and changed their mind

Acceptable variance: confidence can be Low instead of Medium if
tool notes that subscription disputes are inherently difficult
to win without additional usage evidence.

---

## SCENARIO 7
### Subscription Canceled - Weak Case - Accept
Source: Research - 35% of consumers find cancellation difficult

Input:
- Category: Subscription Canceled
- Reason code: Mastercard 4841
- Amount: $49.00
- Dispute rate: 0.7% - triage
- ECI: not applicable - recurring billing
- AVS: not applicable - recurring billing
- CVC: not applicable - recurring billing
- Radar score: not applicable - recurring billing
- Prior orders on fingerprint: 2
- Prior disputes: 0
- Days to dispute: 5
- Pre-dispute customer contact: customer emailed asking how to cancel,
  no merchant response within 48 hours
- Confirmation email: sent but not available to submit
- Return/cancellation policy shown at signup: no
- Product type: subscription

Expected output:
- Classification: Subscription misunderstanding - likely legitimate
- Recommendation: Accept
- Confidence: Medium
- Winnability: Weak - policy not shown at signup, no response to
  cancellation inquiry, confirmation email unavailable
- Triage mode plus weak case equals accept
- Acceptance framing: fix cancellation policy and response time

Acceptable variance: none - both failure signals and triage rate
point clearly to accept.

---

## SCENARIO 8 - MUST PASS
### Refund In Flight Abuse - Dispute
Source: Real merchant story from Shopify community thread

Input:
- Category: Credit Not Processed
- Reason code: Visa 13.7
- Amount: $143.00
- Dispute rate: 0.4% - healthy
- ECI: not applicable - refund scenario
- AVS: not applicable - refund scenario
- CVC: not applicable - refund scenario
- Radar score: not applicable - refund scenario
- Refund history on charge: refund of $143.00 processed
  April 18, 2025 at 2:14pm
- Dispute filed: April 19, 2025 at 9:33am - 19 hours after refund
- Prior orders on fingerprint: 2
- Prior disputes: 0
- Pre-dispute customer contact: yes - customer requested cancellation
  April 17th, merchant processed same day

Expected output:
- Classification: Refund-in-flight abuse
- Recommendation: Challenge
- Confidence: High
- Winnability: Strong
- Critical behavior: this finding MUST appear at the top of the
  analysis section, not buried in paragraph three. Rule 9 requires
  immediate surface. If the refund-in-flight finding appears anywhere
  other than the opening of the analysis, this scenario fails
  regardless of other criteria.

Acceptable variance: none.

---

## SCENARIO 9
### Duplicate Charge - Accept
Source: Stripe category research

Input:
- Category: Duplicate Charge
- Reason code: Visa 12.6
- Amount: $67.00
- Dispute rate: 0.3% - healthy
- ECI: not applicable - duplicate charge scenario
- AVS: not applicable - duplicate charge scenario
- CVC: not applicable - duplicate charge scenario
- Radar score: not applicable - duplicate charge scenario
- Network transaction IDs: two charges with identical IDs
  within 4 minutes
- Prior orders on fingerprint: 3
- Prior disputes: 0
- Pre-dispute customer contact: customer emailed about double charge

Expected output:
- Classification: Genuine duplicate
- Recommendation: Accept
- Confidence: High
- Winnability: Weak - network transaction IDs confirm genuine duplicate
- Acceptance framing: issue refund proactively, contact customer,
  review payment processing setup

Acceptable variance: none - duplicate confirmed by network IDs
is an unambiguous case.

---

## SCENARIO 10
### Descriptor Confusion - Distinct Classification
Source: Research - one-third of cardholders find descriptors confusing

Input:
- Category: Fraudulent
- Reason code: Visa 10.4
- Amount: $52.00
- Dispute rate: 0.2% - healthy
- ECI: 05
- AVS: Y
- CVC: M
- Radar score: 8
- Prior orders on fingerprint: 1 prior order 6 months ago
- Prior disputes: 0
- Days to dispute: 12
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Billing descriptor: NTRPRSE HLTH LLC
- Brand name: NutriPrize Health Co.
- Product type: physical goods
- Confirmation email: sent, available

Expected output:
- Classification: Descriptor confusion - likely not intentional fraud
- Recommendation: Challenge (evidence supports it)
- Confidence: Medium
- Key finding: billing descriptor is unrecognizable relative to
  brand name - flagged as likely cause of dispute
- Descriptor fix instructions must appear as separate actionable note
  outside the main analysis section

Acceptable variance: classification can be Friendly fraud instead
of Descriptor confusion if tool challenges the dispute. The
descriptor fix note must still appear regardless of classification.

---

## SCENARIO 11
### Digital Goods - Software License - Friendly Fraud
Source: Real merchant story from Shopify community - lost despite
proof of license activation after dispute filing

Input:
- Category: Product Not Received
- Reason code: Visa 13.1
- Amount: $39.00
- Dispute rate: 0.4% - healthy
- ECI: 07
- AVS: Y
- CVC: M
- Radar score: 15
- Prior orders on fingerprint: 0
- Prior disputes: 0
- Days to dispute: 3
- Delivery: digital delivery confirmed - license key emailed and
  activated and used after dispute was filed
- Uploaded document: license activation log showing use after
  dispute filing date
- Pre-dispute customer contact: none
- Product type: digital download

Expected output:
- Classification: Friendly fraud
- Recommendation: Challenge
- Confidence: High
- Winnability: Strong - usage after dispute filing is direct evidence
- Fee math: $39 transaction must be noted. Fighting and losing
  costs $30. Tool must acknowledge unfavorable fee math AND still
  recommend challenge based on strength of usage evidence and
  pattern documentation value.

Acceptable variance: none - usage log after dispute filing is
unambiguous.

---

## SCENARIO 12 - MUST PASS
### Low AOV - Fee Math Overrides Winnability
Source: Design session fee math principle, June 2025 Stripe fee change

Input:
- Category: Fraudulent
- Reason code: Visa 10.4
- Amount: $22.00
- Dispute rate: 0.3% - healthy
- ECI: 05
- AVS: Y
- CVC: M
- Radar score: 19
- Prior orders on fingerprint: 1
- Prior disputes: 0
- Days to dispute: 38
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Product type: physical goods

Expected output:
- Classification: Friendly fraud - likely
- Winnability: Moderate
- Recommendation: Accept
- Confidence: Medium
- Critical behavior: fee math must be stated explicitly with the
  exact dollar amounts. "$22 transaction - fighting and losing costs
  $30 - more than the transaction value itself." Fee math must be
  the stated reason for the accept recommendation, not just a note.

Acceptable variance: none - the fee math override is the entire
point of this scenario.

---

## SCENARIO 13 - MUST PASS
### Triage Merchant - Winnable But Accept
Source: Shopify community thread - merchant banned at 0.94%

Input:
- Category: Fraudulent
- Reason code: Visa 10.4
- Amount: $176.00
- Dispute rate: 0.82% - triage and climbing
- ECI: 05
- AVS: Y
- CVC: M
- Radar score: 14
- Prior orders on fingerprint: 2
- Prior disputes: 0
- Days to dispute: 29
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Risk posture: triage

Expected output:
- Classification: Friendly fraud
- Winnability: Strong
- Recommendation: Accept despite strong case
- Confidence: Medium
- Critical behavior: tool must explicitly state this is a winnable
  dispute AND still recommend accepting due to dispute rate. It must
  not just call it a weak case. The tension between winnability and
  merchant situation must be stated directly.
- Downstream consequences of crossing threshold must be named.

Acceptable variance: none - the triage override on a strong case
is the entire point of this scenario.

---

## SCENARIO 14
### Serial Disputer Pattern - Dispute
Source: Design session - charitable default exception for serial abusers

Input:
- Category: Fraudulent
- Reason code: Visa 10.4
- Amount: $94.00
- Dispute rate: 0.4% - healthy
- ECI: 06
- AVS: Y
- CVC: M
- Radar score: 44
- Prior orders on fingerprint: 5
- Prior disputes on this merchant: 2 in past 6 months
- Days to dispute: 22
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Product type: physical goods

Expected output:
- Classification: Friendly fraud - serial pattern
- Recommendation: Challenge
- Confidence: High
- Key finding: two prior disputes in past 6 months is a serial
  abuse pattern. Charitable default does not apply. This must be
  stated explicitly.

Acceptable variance: none.

---

## SCENARIO 15 - ACCEPTABLE VARIANCE
### Family Fraud - Ambiguous
Source: Research - family member using card without cardholder knowledge

Input:
- Category: Fraudulent
- Reason code: Mastercard 4837
- Amount: $127.00
- Dispute rate: 0.3% - healthy
- ECI: 07
- AVS: Y
- CVC: M
- Radar score: 29
- Prior orders on fingerprint: 6
- Prior disputes: 0
- Days to dispute: 9
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Chargeback note: "I did not make this purchase, someone else in
  my household may have used my card"
- Product type: physical goods

Expected output:
- Classification: Ambiguous - family fraud or friendly fraud
- Recommendation: Challenge
- Confidence: Medium
- Competing hypotheses must both be stated

Acceptable variance: classification can be Friendly fraud instead
of Ambiguous. Recommendation must be Challenge. Confidence must
be Medium. If classified as friendly fraud, the chargeback note
must still be cited and addressed.

---

## SCENARIO 16 - MUST PASS
### Reason Code Mismatch - Reclassification and Pipeline Reroute
Source: Design session - reason code reliability bias principle

Input:
- Category: Fraudulent
- Reason code: Visa 10.4 (no authorization)
- Amount: $215.00
- Dispute rate: 0.4% - healthy
- ECI: 05
- AVS: Y
- CVC: M
- Radar score: 11
- Prior orders on fingerprint: 3
- Prior disputes: 0
- Days to dispute: 31
- Delivery: confirmed to billing address
- Pre-dispute customer contact: customer emailed saying product
  arrived damaged with photos attached
- Uploaded document: customer email with photos of damaged product
- Product type: physical goods

Expected output:
- Classification: Product unacceptable - reason code misapplied
- Misapplication flag: true
- Recommendation: depends on product unacceptable evidence - Challenge
- Confidence: Medium
- Critical behavior: reason code mismatch must be flagged explicitly
  at the TOP of the analysis before any other reasoning begins.
  Pipeline must be rerouted to product_unacceptable, not fraudulent.
  If tool analyzes this as a fraudulent dispute without flagging the
  mismatch, this scenario fails regardless of recommendation.

Acceptable variance: none - the mismatch detection and reroute is
the entire point of this scenario.

---

## SCENARIO 17
### Product Unacceptable - Winnable - Dispute
Source: Research and design session

Input:
- Category: Product Unacceptable
- Reason code: Visa 13.3
- Amount: $188.00
- Dispute rate: 0.3% - healthy
- ECI: not applicable - product dispute
- AVS: not applicable - product dispute
- CVC: not applicable - product dispute
- Radar score: 21
- Prior orders on fingerprint: 2
- Prior disputes: 0
- Days to dispute: 19
- Pre-dispute customer contact: customer emailed, merchant responded
  and offered exchange, customer declined and filed dispute
- Confirmation email: sent with product description, available
- Return policy: exists, shown at checkout
- Product type: physical goods
- Uploaded document: confirmation email showing product specs
  that match what was shipped

Expected output:
- Classification: Product unacceptable - likely not legitimate
- Recommendation: Challenge
- Confidence: Medium
- Winnability: Moderate
- Key finding: merchant offered resolution before dispute was filed
  and customer declined. Customer contact record is key evidence.

Acceptable variance: confidence can be Low instead of Medium given
subjectivity of product quality claims.

---

## SCENARIO 18
### Product Unacceptable - Accept
Source: Research - no documentation scenario

Input:
- Category: Product Unacceptable
- Reason code: Mastercard 4853
- Amount: $310.00
- Dispute rate: 0.6% - triage
- ECI: not applicable - product dispute
- AVS: not applicable - product dispute
- CVC: not applicable - product dispute
- Radar score: not applicable - first order, no prior Radar data
- Prior orders on fingerprint: 0
- Prior disputes: 0
- Days to dispute: 7
- Pre-dispute customer contact: customer called and complained,
  merchant has no record of call content
- Confirmation email: not available to submit
- Return policy: exists but not shown at checkout
- Product type: physical goods

Expected output:
- Classification: Product unacceptable - legitimacy unclear
- Recommendation: Accept
- Confidence: Medium
- Winnability: Weak - no confirmation email, policy not shown at
  checkout, first-time customer, triage dispute rate
- Acceptance framing: show policy at checkout, send confirmation
  emails with product specs, keep customer contact records

Acceptable variance: none.

---

## SCENARIO 19
### High Value - Reshipping Address - True Fraud
Source: Research on CNP fraud patterns and design session

Input:
- Category: Fraudulent
- Reason code: Visa 10.4
- Amount: $892.00
- Dispute rate: 0.3% - healthy
- ECI: 07
- AVS: N - no match
- CVC: N - no match
- Radar score: 91
- Prior orders on fingerprint: 0
- Prior disputes: 0
- Days to dispute: 1
- Delivery: delivered to commercial suite address in different
  state from billing address
- Shipping address type: commercial - different state from billing
- Pre-dispute customer contact: none
- Product type: physical goods - high value

Expected output:
- Classification: True unauthorized - high confidence
- Recommendation: Accept
- Confidence: High
- Winnability: Weak - every signal points to card compromise
- Prevention note: Radar rule recommendation for AVS N above
  risk threshold must appear in the output

Acceptable variance: none.

---

## SCENARIO 20 - MUST PASS
### VCE 3.0 Eligible - Dispute with CE3 Lead Strategy
Source: Stripe VCE 3.0 documentation

Input:
- Category: Fraudulent
- Reason code: Visa 10.4
- Amount: $445.00
- Dispute rate: 0.3% - healthy
- ECI: 05
- AVS: Y
- CVC: M
- Radar score: 16
- Prior orders on fingerprint: 3 all within past 90 days,
  all undisputed, customer data matches across all three
- Prior disputes: 0
- Days to dispute: 52
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Card network: Visa

Expected output:
- Classification: Friendly fraud
- Recommendation: Challenge
- Confidence: High
- Winnability: Strong
- Critical behavior: Visa Compelling Evidence 3.0 eligibility must
  be identified. VCE 3.0 qualifying transactions must appear as
  item 1 in evidence_to_submit with Primary weight. If VCE 3.0
  is not identified or does not lead the evidence list, this
  scenario fails regardless of other criteria.

Acceptable variance: none.

---

## SCENARIO 21 - ACCEPTABLE VARIANCE
### Ambiguous - Insufficient Data - Low Confidence
Source: Design session - incomplete data posture

Input:
- Category: Fraudulent
- Reason code: Mastercard 4837
- Amount: $167.00
- Dispute rate: unknown - not provided
- ECI: not available
- AVS: not available
- CVC: M
- Radar score: 48
- Prior orders on fingerprint: 0
- Prior disputes: 0
- Days to dispute: unknown - not provided
- Delivery: not provided
- Pre-dispute customer contact: unknown - not provided
- Product type: physical goods

Expected output:
- Classification: Ambiguous - insufficient data
- Recommendation: Challenge tentatively pending evidence gathering
- Confidence: Low
- Critical behavior: tool must NOT refuse to analyze. Must produce
  a recommendation with stated assumptions and a named list of
  missing evidence. If tool refuses to output a recommendation
  due to missing data, this scenario fails.

Acceptable variance: recommendation can be Accept instead of
Challenge if tool reasons that insufficient data defaults to
accepting rather than fighting blind. Either is acceptable as
long as the missing evidence list is present and the confidence
is Low.

---

## SCENARIO 22
### General Category - Route to Fraudulent Pipeline
Source: Stripe category research

Input:
- Category: General
- Reason code: Visa 10.5 (chip counterfeit - does not apply to CNP)
- Amount: $203.00
- Dispute rate: 0.4% - healthy
- ECI: 05
- AVS: Y
- CVC: M
- Radar score: 21
- Prior orders on fingerprint: 2
- Prior disputes: 0
- Days to dispute: 44
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Product type: physical goods

Expected output:
- Classification: Friendly fraud - reason code mismatch noted
- Recommendation: Challenge
- Confidence: Medium
- Key finding: Visa 10.5 chip counterfeit does not apply to
  card-not-present transactions. Misapplied reason code.
  General category routed to fraudulent pipeline per rules.

Acceptable variance: confidence can be Low instead of Medium if
tool notes the General category ambiguity as a limiting factor.

---

## SCENARIO 23
### Credit Not Processed - Genuine - Accept
Source: Design session pipeline definitions

Input:
- Category: Credit Not Processed
- Reason code: Visa 13.7
- Amount: $118.00
- Dispute rate: 0.3% - healthy
- ECI: not applicable - refund scenario
- AVS: not applicable - refund scenario
- CVC: not applicable - refund scenario
- Radar score: not applicable - refund scenario
- Refund history on charge: no refund issued
- Days to dispute: 28
- Pre-dispute customer contact: customer emailed twice requesting
  refund, no merchant response
- Return policy: exists, shown at checkout, item qualifies
  for return within 30 days
- Product type: physical goods

Expected output:
- Classification: Genuine credit not processed
- Recommendation: Accept
- Confidence: High
- Key finding: customer was entitled to a refund, contacted merchant
  twice, received no response. Correct consumer protection outcome.
- Acceptance framing: issue refund immediately, this was preventable

Acceptable variance: none - entitlement plus no merchant response
is unambiguous.

---

## SCENARIO 24 - ACCEPTABLE VARIANCE
### Proactive Merchant - First Dispute Ever - Ambiguous
Source: Design session - proactive merchant risk posture

Input:
- Category: Fraudulent
- Reason code: Visa 10.4
- Amount: $74.00
- Dispute rate: 0.1% - healthy
- Risk posture: proactive
- ECI: 07
- AVS: Y
- CVC: M
- Radar score: 33
- Prior orders on fingerprint: 0
- Prior disputes: 0
- Days to dispute: 5
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Product type: physical goods

Expected output:
- Classification: Ambiguous - true fraud and friendly fraud both
  plausible
- Recommendation: Challenge
- Confidence: Low
- Fee math: $74 - just under $75 threshold. Must be noted.
- Educational framing appropriate for proactive merchant

Acceptable variance: classification can be True unauthorized or
Friendly fraud instead of Ambiguous given mixed signals. Confidence
must be Low or Medium. Recommendation must be Challenge given
proactive posture and healthy dispute rate.

---

## SCENARIO 25
### Order Velocity - Bulk Purchase Before Dispute
Source: Design session serial disputer, TikTok chargeback hack research

Input:
- Category: Fraudulent
- Reason code: Visa 10.4
- Amount: $341.00 (this dispute)
- Dispute rate: 0.5% - caution
- ECI: 06
- AVS: Y
- CVC: M
- Radar score: 52
- Prior orders on fingerprint: 7 orders in past 30 days,
  total value $1,847
- Prior disputes on this merchant: 0 before this batch
- Days to dispute on this order: 18
- Additional context: 3 other disputes from same card fingerprint
  filed same week against this merchant
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Product type: physical goods - high resale value

Expected output:
- Classification: Friendly fraud - organized abuse pattern
- Recommendation: Challenge all disputes in this batch
- Confidence: High
- Charitable default: does not apply - must be stated explicitly
- Key finding: 7 orders totaling $1,847 followed by multiple
  simultaneous disputes is a warehousing pattern
- Note: block this card fingerprint from future orders

Acceptable variance: confidence can be Medium instead of High
if tool notes that individual case evidence is moderate despite
the pattern being clear.

---

## SCENARIO 26 - MUST PASS
### Evaluator Loop Test - Incomplete First Pass
Source: Architecture requirement - evaluator-optimizer pattern

Purpose: This scenario is specifically designed to produce a
first-pass synthesis output that fails the evaluator on criterion 2
(confidence justification) and criterion 5 (two-question framework).
The pass condition is that the evaluator catches both failures,
returns revision instructions, and the revised output passes all
eight criteria. This tests the evaluator-optimizer loop, not just
the synthesis prompt.

Input (same as Scenario 1 - friendly fraud high confidence):
- Category: Fraudulent
- Reason code: Visa 10.4
- Amount: $284.00
- Dispute rate: 0.3% - healthy
- ECI: 05
- Wallet: Apple Pay
- AVS: Y
- CVC: M
- Radar score: 12
- Prior orders on fingerprint: 2
- Prior disputes: 0
- Days to dispute: 47
- Delivery: confirmed to billing address
- Pre-dispute customer contact: none
- Product type: physical goods

Simulated first-pass output to feed the evaluator:
Feed this deliberately flawed output to the evaluator prompt to
test the loop:

"This dispute may potentially be friendly fraud. The customer has
prior orders on this card. We recommend challenging this dispute.
The merchant's dispute rate is healthy."

Expected evaluator output:
- overall_result: revision_required
- Failed criteria must include at minimum:
  - confidence_justification: fail (no signal count, no named sources)
  - two_question_framework: fail (winnability not assessed,
    merchant situation not addressed separately)
  - citation_completeness: fail (no sources named)
  - verdict_format: fail (no confidence level stated, no IS NOT)
  - no_false_confidence: fail ("may potentially" contradicts implied
    high confidence recommendation)
- revision_instructions must be specific and actionable

Pass condition: evaluator correctly identifies at least four
failing criteria and returns specific revision instructions for
each. A pass here confirms the loop will catch real failures
in production.

Acceptable variance: evaluator can identify more than four failing
criteria. Any superset of the expected failures is a pass.
Missing even one of the five listed failures is a fail.

---

## Complete Scoring Reference

Total scenarios: 26
Must-pass scenarios (zero tolerance): 1, 2, 8, 12, 13, 16, 20, 26
Acceptable variance scenarios: 4, 15, 21, 24
Standard scenarios: all others

Target before launch:
- Must-pass: 8/8 - no exceptions, launch blocking
- Overall: 23/26 minimum

When a scenario fails, document:
- Which of the six prompts produced the incorrect output
- Which specific instruction was missing or insufficient
- The exact revision needed before re-running the dataset

Re-run the full dataset after any prompt revision. Never re-run
only the failed scenario in isolation - prompt changes can affect
other scenarios unexpectedly.
