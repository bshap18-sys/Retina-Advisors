# Retina Advisors Dispute Analyzer - Design Decisions

This document captures all design decisions, research findings, and reasoning established before the build began. It is the source of truth for the system prompt, eval dataset, and input form. Do not skip this document in a new session.

Last updated: April 23, 2025

---

## Core Analytical Principles

These are the fraud expertise principles that separate this tool from a generic AI wrapper. All must be encoded explicitly in the system prompt - not as general instructions but as specific analytical rules.

### 1. Behavioral inference over surface signals
Don't just evaluate what the data says. Evaluate what the data implies about human behavior. The absence of expected behavior is as meaningful as the presence of suspicious behavior. A fraud analyst reads the behavioral story behind the numbers.

### 2. Timeline as behavioral fingerprint
When a dispute is filed tells a different story than the fact that it was filed. Three distinct patterns:
- Dispute filed 0-3 days after delivery with no prior merchant contact: opportunistic friendly fraud or genuine immediate problem - pre-dispute contact field distinguishes them
- Dispute filed 90-110 days after transaction: calculated behavior, waiting near the dispute window. True fraud victims dispute immediately. Waiting 90 days is a friendly fraud fingerprint.
- Dispute filed same day as delivery: cardholder never gave the merchant a chance to respond. Behavioral red flag.

### 3. Identity coherence across contact signals
Look for coherence across all identity signals, not just obvious fakes. Subtle mismatches matter: name inconsistent with email pattern, email account created same month as order, shipping address is a freight forwarder or reshipping service, phone number region inconsistent with billing address. No single signal is proof - the pattern across signals builds the profile.

### 4. Reason code reliability bias - critical
Reason codes are the cardholder's stated complaint, not necessarily their actual complaint. Cardholders often don't select their own reason code - a bank rep does. Misapplication is common: "no cardholder authorization" selected when the real issue was a defective product; "credit not processed" selected for a duplicate charge. The system must cross-reference the reason code against all other available signals before accepting it at face value. A reason code that doesn't cohere with the evidence is itself a signal worth surfacing in the output.

### 5. Charitable default with evidence override
The base rate of intentional fraud is low. Most dispute filers are not trying to defraud anyone - they had a bad experience, misunderstood the process, or are confused about a charge. The default analytical posture is charitable: assume something went wrong before assuming deliberate fraud. The classification earns its confidence level when evidence stacks up against the charitable explanation. A model that defaults to assuming fraud will over-classify and under-recommend challenging.

This charitable default does not apply when serial disputer signals are present. Someone filing disputes across multiple merchants in a pattern is operating with deliberate intent. The Stripe customer history and prior dispute fields are the primary signals for this.

### 6. True unauthorized vs friendly fraud - the coherence test
True unauthorized fraud shows behavioral anomaly relative to the cardholder's established history. The transaction doesn't look like them - it deviates from their normal purchase category, amount range, or fulfillment pattern. The card was used by someone who isn't the cardholder.

Friendly fraud shows behavioral coherence - the disputed transaction fits perfectly into the cardholder's history because it was made by the cardholder. Same device, same purchase pattern, consistent amount. That coherence is a classification signal, not exoneration.

The chargeback note (when available) follows the same logic. A genuine fraud victim writes like someone who just discovered a compromise - specific, confused, mentions when they found it. A friendly fraud note is often vague, formulaic, or inconsistent with the other evidence.

Honest limitation: the strongest signals for this distinction - true account age at the issuer level, cross-merchant dispute history, device fingerprint - are not available via Stripe. The tool must work with what Stripe surfaces and acknowledge this limitation rather than project false confidence.

### 7. Account history weight
Dispute history, transaction history, and dollar amount only have meaning in context of each other. A $40 dispute on a first-ever order looks different from a $40 dispute on an account with 12 prior orders and two prior disputes. The number alone means nothing. The number relative to the account's behavioral baseline is everything. Always evaluate signals relative to that customer's established pattern, not in isolation.

### 8. Billing descriptor confusion - a distinct classification
A significant portion of "fraudulent" disputes are not fraud and not intentional friendly fraud - they are genuine confusion. The customer didn't recognize the charge on their statement because the billing descriptor shows the merchant's legal entity name, not their brand name. One-third of cardholders report finding billing descriptors confusing or unrecognizable. Nearly three-quarters of merchants don't know what their own descriptor looks like.

Classification signal: a "fraudulent" dispute from a clean customer profile with no prior disputes and a coherent transaction pattern may be descriptor confusion, not fraud. The tool should flag this as a distinct possibility and note it as a preventable problem the merchant can fix.

### 9. Refund-in-flight abuse
A specific fraud pattern where a customer requests cancellation, the merchant processes the refund, and the customer files a chargeback the next day anyway - effectively getting paid twice. The refund timestamp versus dispute filing date is the entire case. If refund history on the charge object shows a refund was processed before the dispute was filed, the tool must flag this as refund-in-flight abuse with its own evidence strategy: the refund record with timestamp is exhibit one.

---

## The Core Purpose

This tool does the fraud classification job that Stripe deliberately does not do. Stripe's categorization is optimized for evidence submission guidance. Our tool is optimized for expert fraud analysis - distinguishing true fraud from friendly fraud, assessing winnability, and giving a recommendation calibrated to the merchant's specific situation.

That distinction is the entire value proposition. Do not let the tool collapse back into evidence submission guidance. That is Stripe's job. This tool tells the merchant what they are actually dealing with and whether fighting makes sense given their circumstances.

---

## The Stripe Category Bias Problem

This is critical context for the system prompt.

Stripe maps all dispute reason codes into seven categories. The category names create implicit bias that the tool must actively counteract.

"Fraudulent" category bias: Merchants assume this means card compromise - a criminal used their customer's card. In reality, a large portion of DTC "Fraudulent" disputes are friendly fraud - the legitimate cardholder made the purchase, received it, and told their bank they didn't recognize it. This is a winnable dispute with the right evidence. The tool must not inherit the "criminal = accept" framing.

"Product Not Received" category bias: Merchants assume an honest customer or a carrier problem. In reality, product not received is a common friendly fraud vector - customer receives the package, claims they didn't, disputes. The category implies fulfillment failure when the pattern may indicate behavior fraud.

The rule: The Stripe category is one signal among many. The system prompt must explicitly instruct the model to treat the category as a starting point for investigation, not a conclusion. The model must actively reason against the implied narrative of the category name using all available signals.

---

## Stripe's Seven Dispute Categories

These map directly to our routing step. The routing call reads the Stripe category field and routes to the appropriate analysis pipeline.

1. Fraudulent - highest volume for DTC, most analytical complexity, requires true fraud vs friendly fraud sub-classification
2. Product Not Received - second highest volume, delivery confirmation is the load-bearing signal
3. Product Unacceptable - item not as described, quality disputes
4. Subscription Canceled - recurring billing disputes, cancellation evidence is key
5. Credit Not Processed - merchant promised refund, didn't deliver
6. Duplicate Charge - technical/processing error category
7. General - catch-all for disputes that don't fit other categories

Volume expectation for DTC merchants: Fraudulent 60-70%, Product Not Received 20-25%, remainder split across others.

Important: The "Fraudulent" pipeline does significantly more work than others. It must answer the true fraud vs friendly fraud sub-question before generating a recommendation. That sub-classification drives a completely different evidence strategy and recommendation.

---

## Two-Question Framework for Every Dispute

Every analysis must answer two distinct questions in order. Conflating them produces bad recommendations.

Question 1 - Is this dispute winnable?
This is about the specific transaction evidence. What does the evidence say about what actually happened?

Question 2 - Should this merchant fight it given their situation?
This is about merchant context. Even a winnable dispute may not be worth fighting depending on the merchant's dispute rate, risk appetite, and strategic goals.

A merchant near the Visa 0.9% or Mastercard 1% threshold may be better served accepting a winnable dispute than risking the incremental rate impact and counter-dispute fee. A healthy merchant may choose to fight unwinnable disputes specifically to document friendly fraud patterns and deter repeat offenders.

The recommendation must always address both questions explicitly.

---

## Merchant Risk Posture - Three Situations

The tool must identify which situation the merchant is in before generating a recommendation.

Triage mode: Approaching card network thresholds. Dispute rate near or above 0.5% and climbing. Every dispute decision has rate implications. Accepting strategically may be correct even for winnable disputes. Note: platforms act before official thresholds. Real-world evidence shows merchants getting account holds at 0.94% despite Shopify's stated 1% threshold. The danger zone starts at 0.5%, not 0.75%.

Healthy with runway: Dispute rate well below 0.5%. Can afford to fight patterns worth documenting. Paper trail from disputes deters repeat friendly fraud even when you lose.

Proactive: Not yet in trouble. Wants to understand what they are looking at and build good habits. Educational framing appropriate alongside recommendation.

Note on dispute rate awareness: Merchants with a problem typically know their rate - it is prominent in Stripe Analytics. Merchants without a problem may not. The tool should note where to find it in Stripe if the merchant reports they do not know it.

Stripe's two rate calculations (important distinction):
- Dispute activity: disputes by dispute date - what card networks use for monitoring programs
- Dispute rate: disputes by charge date - more accurate for pattern analysis

For the merchant context input, ask for their current dispute rate and flag which calculation Stripe is showing them.

---

## Fee Structure - Updated June 2025

Stripe's dispute fee structure as of June 17, 2025:
- Base dispute fee: $15 (charged on all disputes regardless of outcome)
- Counter fee: additional $15 if merchant submits evidence and loses
- Total cost of a lost challenged dispute: $30
- Total cost of a won challenged dispute: $15
- Total cost of accepting without challenging: $15

Implication for recommendations: transaction amount must be factored against fee exposure. For low average order value merchants, the math on a weak case can make accepting the financially correct decision even when the dispute is winnable. The tool must surface this calculation explicitly when the dispute amount is low relative to the $30 worst-case fee.

---

## Data Architecture - Six Layers

Layer 1 - Stripe dispute object (automatic pull via Stripe MCP):
Dispute reason code, Stripe category, amount, currency, customer name, customer email, billing address, purchase IP, evidence due date, dispute status, Visa Compelling Evidence 3.0 eligibility flag

Layer 2 - Stripe charge object expansion (automatic pull via Stripe MCP - second call):
ECI indicator, wallet type (Apple Pay / Google Pay / standard), card fingerprint, AVS result, CVC result, 3DS authentication outcome, card brand, card funding type (credit / debit / prepaid), network transaction ID, Radar risk score (0-100), Radar risk level (normal / elevated / highest), Radar rule that fired if any, merchant metadata on the charge (order ID, product info), refund history on the charge including timestamps

Layer 3 - Customer history query (automatic pull via Stripe MCP - third call):
Prior transaction history by card fingerprint or customer ID, prior disputes from this customer, order velocity (multiple orders in short window before dispute)

Layer 4 - Custom delivery MCP server (automatic pull):
Delivery status lookup by tracking number and carrier. This is a custom MCP server built for this project - demonstrates Bryan can build MCP servers, not just connect to existing ones.

Layer 5 - Merchant manual inputs (form):
See input form fields section below.

Layer 6 - Document uploads (evidence files):
PDFs, images, screenshots processed directly by Claude. Delivery confirmation photos, customer email threads, product photos. Separate upload section, not form fields. Demonstrates Claude's native PDF and image handling capability.

---

## Input Form Fields - Load-Bearing Only

These are fields where a different value produces a genuinely different recommendation. Non-load-bearing fields were intentionally excluded to keep the form lean.

Merchant context (set once, applies to all disputes):
- Current dispute rate (self-reported, v1 - auto-calculate in v2)
- MCC (single value per merchant)
- Risk posture / appetite (triage / healthy / proactive)
- Billing descriptor (what appears on customer statements - used to assess descriptor confusion risk)

Fulfillment data:
- Tracking number
- Carrier
- Ship date
- Delivery date
- Delivery confirmation status (confirmed / unconfirmed / failed)
- Billing address matched shipping address (yes / no)

Customer contact data:
- Did customer contact merchant before filing dispute? (yes / no) - critical friendly fraud signal
- Did merchant contact customer before dispute? (yes / no)
- Notes from any customer contact exchange

Order context:
- Product type (physical goods / digital download / subscription / service)
- Confirmation email sent (yes / no / have it available to submit)

Policy data:
- Refund / return policy exists (yes / no)
- Policy shown at checkout (yes / no)

Fields excluded from v1 (move to v2):
- Auto-calculated dispute rate from Stripe history
- Shipping method (color, not load-bearing)

---

## Load-Bearing Fields by Dispute Category

Fraudulent (True Fraud vs Friendly Fraud sub-classification):
Winnability signals: ECI / 3DS result, card fingerprint match to prior purchases, customer transaction history, order velocity, AVS and CVC results, Radar score, wallet type, billing descriptor coherence
Merchant context signals: dispute rate, prior disputes from this customer, pre-dispute customer contact (did they complain before disputing - friendly fraud signal)

Product Not Received:
Winnability signals: delivery confirmation status (the single most important field), billing/shipping address match, tracking proof of delivery to address on file
Merchant context signals: dispute rate, customer history with merchant

Product Unacceptable:
Winnability signals: product type, confirmation email (what was promised vs delivered), return policy shown at checkout, customer contact history
Merchant context signals: dispute rate, prior disputes from this customer

Subscription Canceled:
Winnability signals: confirmation email (terms agreed to), return/cancellation policy shown at signup, customer contact history, any usage after alleged cancellation date
Merchant context signals: dispute rate

Credit Not Processed:
Winnability signals: refund history on charge object including timestamps (was refund actually issued before dispute was filed?), customer contact history
Merchant context signals: dispute rate

Duplicate Charge:
Winnability signals: charge metadata, network transaction ID, transaction history
Merchant context signals: rarely changes recommendation - usually accept or fight based purely on evidence

General:
Treat as Fraudulent pipeline by default. Flag to merchant that reason code is ambiguous.

---

## Report Output Structure - Decided

Structure locked as Option B hybrid. Hierarchy:

1. Dispute header - dispute ID, dollar amount, evidence due date (at a glance, top of report)
2. Verdict block - green left-border accent, leads with recommendation and one-sentence summary in plain English
3. Metric cards - classification, winnability, dispute rate status, confidence level (four cards in a row)
4. Reason code plain English translation - one line explaining what the reason code actually means in plain language before the analysis begins
5. Why we think this - analytical reasoning in plain English with professional precision, no jargon without explanation
6. Evidence to submit - numbered list, priority ordered, each item cited to its source

Voice: senior fraud expert speaking to a non-technical business owner. Clear and decisive. Professional precision without unnecessary jargon. Terms like "friendly fraud," "compelling evidence," "ECI indicator" used correctly and explained briefly in context. Formal enough that a fraud SaaS professional reading it recognizes the expertise behind it.

On confidence levels: surface realistic expectations. Even Stripe's maximum win likelihood represents roughly 60% win rate. Never project false confidence.

---

## Recommendation Output Content Requirements

Every recommendation must contain all of the following:

1. Dispute classification - what this dispute actually is with reasoning
2. Reason code plain English translation - what this code actually means, not the technical definition
3. Winnability assessment - strong / moderate / weak with specific evidence driving it
4. Fee math when relevant - for low AOV disputes, surface the $15/$30 fee exposure vs dispute amount
5. Merchant situation context - how dispute rate and risk posture affect the recommendation
6. Recommendation - dispute or accept, with confidence level (high / medium / low)
7. Reasoning - explicit explanation connecting evidence to recommendation
8. If disputing - exact evidence to submit, specific and actionable, tied to dispute category requirements
9. If accepting - why accepting is the right strategic call, not just a default
10. Citations - every claim traces to a named source (Stripe data field, merchant input, or delivery MCP result)
11. If descriptor confusion is suspected - flag it as a separate actionable note with instructions for how to fix the billing descriptor in Stripe

---

## Architecture Patterns - Required, Non-Negotiable

All eight must be present and identifiable in the codebase.

1. Routing - first Claude call reads Stripe category and dispute signals, classifies dispute type, routes to correct analysis pipeline
2. Parallelization - four simultaneous Claude calls: delivery/fulfillment evidence, customer behavior evidence, transaction risk indicators, dispute reason code analysis
3. Evaluator-Optimizer - second Claude call validates recommendation meets quality criteria (all output sections present, confidence level justified, citations complete), loops if it fails
4. Structured output with citations - every claim in report traces to named source
5. MCP tool use - Stripe official MCP + custom Python delivery status MCP server
6. Prompt eval pipeline - scored test cases against eval dataset, not cherry-picked demos
7. Temperature 0.0-0.3 - set from first API call, documented in code comments
8. Prompt caching - on system prompt from first request

Fraud analogies for each pattern (use in README and explanations):
- Routing = fraud rule triage, classify before you investigate
- Parallelization = running card network rules and ML model simultaneously, don't wait for one to finish before starting another
- Evaluator-Optimizer = backtesting a fraud rule before deploying it, validate before you commit
- Low temperature = rules engine vs model score, fraud analysis needs consistency not creativity
- Prompt caching = don't re-run your baseline checks on every transaction, cache what doesn't change

---

## Version 2 Roadmap (README only - do not build in v1)

- Auto-calculate dispute rate from Stripe charge and dispute history
- Shopify MCP integration
- Email / communication history analysis for pre-dispute contact detection
- Aggregated pattern analysis across dispute history
- Stripe Radar rule recommendations
- Shipping method as additional fulfillment signal

---

## Key Positioning to Maintain

- "Stripe Radar is the scalpel, you're the surgeon" - core consulting line
- This tool does what Stripe doesn't: fraud classification, not just evidence guidance
- The architecture is the product, not just the use case
- Bryan sits at the intersection of fraud domain expertise AND AI building capability
- Target employer audience: Sardine, Socure, Sift, Stripe, Alloy, Unit21, Prove
