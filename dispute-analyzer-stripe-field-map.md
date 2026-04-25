# Stripe Field Mapping - Pre-Code Gate Artifact

This document validates every field listed in `dispute-analyzer-design-decisions.md` Layers 1, 2, and 3 against the canonical Stripe API reference. It closes the pre-code gate item "Stripe MCP field research - confirm input form maps to real Stripe dispute fields."

Sources of truth:
- https://docs.stripe.com/api/disputes/object
- https://docs.stripe.com/api/charges/object

Verified against live test dispute `du_1TQAhO0BuWfcB30e3qJ8C9gt` on 2026-04-25.

---

## Headline Findings

1. **One critical issue.** Layer 1 lists customer name, customer email, billing address, and purchase IP as Stripe-supplied dispute fields. They exist on the Dispute object only inside `evidence.*`, which is a **merchant-supplied evidence submission slot**, not Stripe ground truth. Default values are null. The real customer data lives on the **Charge object's** `billing_details.*` and must be pulled from there. This is a field-provenance bug in the design, not a wording issue. If the analyzer reads from `dispute.evidence.customer_email_address` it will see null until the merchant submits evidence, defeating the purpose.

2. **One terminology conflation.** Layer 1 says "Dispute reason code" and "Stripe category" as if they are two distinct fields. They are not. The Dispute object's top-level `reason` IS the Stripe-bucketed category (one of the seven). The granular underlying network reason code (e.g. Visa `10.4`, Mastercard `4837`) lives at `payment_method_details.card.network_reason_code` and is a different field. Both are useful and the analyzer wants both, but the design should name them correctly.

3. **One field-shape correction.** Layer 2 says "AVS result" as a single field. Stripe does not expose a merged AVS code on the modern Charge object. It exposes two separate checks: `payment_method_details.card.checks.address_line1_check` and `address_postal_code_check`. The analyzer must combine them into a verdict.

4. **Several missing high-value fields** the design should consider adding to Layer 2 (see "Recommended additions" section below). None are blockers.

5. **Everything else maps cleanly.** Roughly 80% of the design's named fields map one-to-one to real Stripe paths.

---

## Layer 1 - Dispute Object Fields

| Design field | Stripe path | Status | Notes |
|---|---|---|---|
| Dispute reason code (Stripe category) | `reason` | OK | Top-level enum, one of the seven Stripe categories. Renaming this in the design from "reason code" to "category" would prevent confusion with network_reason_code. |
| Granular network reason code | `payment_method_details.card.network_reason_code` | MISSING from design | Visa `10.4`, MC `4837`, etc. Critical for the reason-code analysis pipeline (architecture pattern 2, parallel call 4). Add to Layer 1. |
| Amount | `amount` | OK | Integer, smallest currency unit |
| Currency | `currency` | OK | ISO 4217 lowercase |
| Customer name | `evidence.customer_name` | WRONG SOURCE | Pull from Charge's `billing_details.name` instead. Dispute's evidence.customer_name is merchant-supplied and null by default. |
| Customer email | `evidence.customer_email_address` | WRONG SOURCE | Pull from Charge's `billing_details.email` or `receipt_email` instead. |
| Billing address | `evidence.billing_address` | WRONG SOURCE | Pull from Charge's `billing_details.address.*` (six subfields). |
| Purchase IP | `evidence.customer_purchase_ip` | WRONG SOURCE | Not directly on Charge either. Lives on the underlying PaymentIntent or Radar session. Mark as best-effort, may be unavailable. |
| Evidence due date | `evidence_details.due_by` | OK | Unix timestamp, nullable |
| Dispute status | `status` | OK | Enum: `warning_needs_response`, `needs_response`, `under_review`, `won`, `lost`, etc. |
| Visa CE3 eligibility flag | `evidence_details.enhanced_eligibility.visa_compelling_evidence_3.status` | OK | Plus top-level `enhanced_eligibility_types` array. Status enum: `qualified`, `not_qualified`, `requires_action`. Includes `required_actions` array detailing what's missing. |

**Additional Layer 1 fields worth adding:**

| Stripe path | Why it matters |
|---|---|
| `is_charge_refundable` | Tells the analyzer whether "issue refund instead of fighting" is even an option |
| `balance_transactions[]` | The actual debit and any reversal, with timestamps. Refund-in-flight detection (design principle #9) needs this. |
| `payment_method_details.card.case_type` | `chargeback` vs `inquiry` vs `block`. Inquiries have different response strategies than chargebacks. |
| `payment_intent` | Linkage for pulling the underlying PaymentIntent if needed |
| `created` | Dispute filing timestamp. Combined with charge `created`, gives the timeline-as-fingerprint signal (design principle #2). |

---

## Layer 2 - Charge Object Fields

| Design field | Stripe path | Status | Notes |
|---|---|---|---|
| ECI indicator | `payment_method_details.card.three_d_secure.electronic_commerce_indicator` | OK | Only populated when 3DS was used. Null otherwise. |
| Wallet type | `payment_method_details.card.wallet.type` | OK | More granular than design says. Enum includes `apple_pay`, `google_pay`, `samsung_pay`, `link`, `visa_checkout`, `amex_express_checkout`, `click_to_pay`, `masterpass`. "Standard" = wallet object is null. |
| Card fingerprint | `payment_method_details.card.fingerprint` | OK | The cross-charge identity signal |
| AVS result | `payment_method_details.card.checks.address_line1_check` + `address_postal_code_check` | NEEDS COMBINING | Two fields, each `pass`/`fail`/`unavailable`/`unchecked`. Analyzer must combine into a verdict. |
| CVC result | `payment_method_details.card.checks.cvc_check` | OK | Same enum |
| 3DS authentication outcome | `payment_method_details.card.three_d_secure.result` | OK | Plus `authentication_flow` (`challenge` / `frictionless`) and `version` are useful adjacent signals. |
| Card brand | `payment_method_details.card.brand` | OK | |
| Card funding type | `payment_method_details.card.funding` | OK | `credit` / `debit` / `prepaid` / `unknown` |
| Network transaction ID | `payment_method_details.card.network_transaction_id` | OK | |
| Radar risk score (0-100) | `outcome.risk_score` | OK | |
| Radar risk level | `outcome.risk_level` | OK | `normal` / `elevated` / `highest` / `not_assessed` |
| Radar rule that fired | `outcome.rule` | OK | Single rule ID, expandable |
| Merchant metadata on charge | `metadata` | OK | Free-form key-value object |
| Refund history with timestamps | `refunds.data[]` (each item has `created`, `amount`, `id`) | OK | Refund-in-flight detection (design principle #9) reads from here |

**Recommended additions to Layer 2:**

| Stripe path | Why it matters |
|---|---|
| `outcome.seller_message` | Stripe's plain English verdict ("Payment complete", "Stripe blocked this payment as fraudulent"). Useful for the report's narrative, and free signal. |
| `payment_method_details.card.country` | Card-issuing country. Cross-border purchase signal for friendly fraud detection. |
| `payment_method_details.card.last4` | For evidence packets and customer correspondence references |
| `payment_method_details.card.network_token.used` | Whether Stripe used a network token. CE3-relevant signal. |
| `fraud_details.stripe_report` | Stripe's own fraud assessment if it flagged the charge as fraudulent at authorization time |
| `fraud_details.user_report` | Whether the merchant has previously reported this charge as `safe` or `fraudulent`. Surfaces merchant prior knowledge. |
| `radar_options.session` | Radar session ID, snapshot of browser metadata and device details. Adjacent to identity-coherence signals (design principle #3). |
| `receipt_email` | Distinct from `billing_details.email`. Sometimes the email used at checkout differs from the billing email; mismatch is itself a signal. |
| `three_d_secure.exemption_indicator` | Issuer-granted 3DS exemption. Affects liability shift assessment for the recommendation. |
| `disputed` (boolean) and `dispute` (linkage) | The reverse linkage. Confirms the analyzer is looking at the right charge. |

---

## Layer 3 - Customer History

The design specifies "Prior transaction history by card fingerprint or customer ID, prior disputes from this customer, order velocity." These are not single fields; they are derived from separate API list calls:

- Prior transactions: `GET /v1/charges?customer={id}` or filtered by fingerprint
- Prior disputes: `GET /v1/disputes?charge={id}` per prior charge, or `?payment_intent={id}`
- Order velocity: derived by sorting prior charges by `created` and counting in time windows

Field-level mapping for Layer 3 is deferred to implementation time when the customer history MCP call is built. No design changes required here, but flag in build notes that this layer is multi-call, not single-object.

---

## Action Items for the Design Document

The following corrections should be applied to `dispute-analyzer-design-decisions.md`:

1. Layer 1: move customer name, email, billing address, and purchase IP **out** of the dispute object section and **into** Layer 2 (charge object). Note that purchase IP is best-effort and may be null.
2. Layer 1: rename "Dispute reason code" to "Stripe category (the `reason` field)". Add a separate line item "Granular network reason code" with the path `payment_method_details.card.network_reason_code`.
3. Layer 1: add `is_charge_refundable`, `balance_transactions[]`, `payment_method_details.card.case_type`, `payment_intent`, and `created` (dispute filing timestamp).
4. Layer 2: clarify that "AVS result" is two underlying checks (`address_line1_check` and `address_postal_code_check`) that the analyzer combines.
5. Layer 2: consider adding `outcome.seller_message`, `card.country`, `card.last4`, `card.network_token.used`, `fraud_details.*`, `radar_options.session`, `three_d_secure.exemption_indicator`, and `receipt_email`.

These are corrections to a pre-code design document, not code changes. No application code is affected because none has been written.
