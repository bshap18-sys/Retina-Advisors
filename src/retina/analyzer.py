import asyncio
import json

from anthropic import AsyncAnthropic

from retina.prompts import (
    BEHAVIOR_PROMPT,
    DELIVERY_PROMPT,
    EVALUATOR_PROMPT,
    REASON_CODE_PROMPT,
    ROUTING_PROMPT,
    SYNTHESIS_PROMPT,
    TRANSACTION_RISK_PROMPT,
)

client = AsyncAnthropic()

MODEL = "claude-sonnet-4-6"

# Temperature 0.1 on all calls - fraud classification is a rules engine,
# not a creative task. Deterministic behavior across repeated runs is
# required. Never change without a documented reason.
TEMPERATURE = 0.1

MAX_EVALUATOR_LOOPS = 3


async def _call_claude(system_prompt: str, user_content: str) -> str:
    """Single reusable async helper. All seven calls go through here.

    System parameter is a list with cache_control so the Anthropic SDK
    enables prompt caching on every call. A plain string does not accept
    cache_control - the list format is required.
    """
    system = [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    response = await client.messages.create(
        model=MODEL,
        max_tokens=4096,
        temperature=TEMPERATURE,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


async def route_dispute(dispute_input: dict) -> dict:
    """Call 0: classify dispute type and select analysis pipeline.

    Fires before asyncio.gather. Extracts only the fast signals needed
    for routing - not the full dict - so this call stays cheap.
    """
    refund_before_dispute = bool(dispute_input.get("refund_history"))

    routing_slice = {
        "dispute_category": dispute_input.get("dispute_category"),
        "network_reason_code": dispute_input.get("network_reason_code"),
        "card_network": dispute_input.get("card_network"),
        "dispute_amount": dispute_input.get("dispute_amount"),
        "prior_orders_count": dispute_input.get("prior_orders_count"),
        "days_to_dispute": dispute_input.get("days_to_dispute"),
        "eci_indicator": dispute_input.get("eci_indicator"),
        "wallet_type": dispute_input.get("wallet_type"),
        "avs_result": dispute_input.get("avs_result"),
        "radar_score": dispute_input.get("radar_score"),
        "refund_before_dispute": refund_before_dispute,
        "refund_history": dispute_input.get("refund_history", []),
        "merchant_context": dispute_input.get("merchant_context", {}),
    }

    user_content = json.dumps(routing_slice, indent=2)

    try:
        raw = await _call_claude(ROUTING_PROMPT, user_content)
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "pipeline": "general_ambiguous",
            "confidence": "low",
            "rationale": (
                "Routing call returned unparseable output - defaulting to general_ambiguous."
            ),
            "parse_error": True,
        }


async def analyze_delivery(dispute_input: dict) -> dict:
    """Call 1 (parallel): evaluate delivery and fulfillment evidence."""
    delivery_slice = {
        "dispute_category": dispute_input.get("dispute_category"),
        "dispute_amount": dispute_input.get("dispute_amount"),
        "days_to_dispute": dispute_input.get("days_to_dispute"),
        "fulfillment_data": dispute_input.get("fulfillment_data", {}),
        "delivery_status": dispute_input.get("delivery_status", {}),
        "customer_billing_address": dispute_input.get("customer_billing_address", {}),
        "dispute_filed_timestamp": dispute_input.get("dispute_filed_timestamp"),
    }

    user_content = json.dumps(delivery_slice, indent=2)

    try:
        raw = await _call_claude(DELIVERY_PROMPT, user_content)
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "fulfillment_score": None,
            "delivery_confirmed": None,
            "delivery_date": None,
            "dispute_filed_days_after_delivery": None,
            "address_match": None,
            "shipping_address_type": None,
            "timeline_flags": [],
            "key_signals": [],
            "red_flags": [],
            "missing_evidence": ["delivery_analysis parse error - all fields null"],
            "parse_error": True,
        }


async def analyze_behavior(dispute_input: dict) -> dict:
    """Call 2 (parallel): evaluate customer behavior signals."""
    behavior_slice = {
        "dispute_category": dispute_input.get("dispute_category"),
        "dispute_amount": dispute_input.get("dispute_amount"),
        "prior_orders_count": dispute_input.get("prior_orders_count"),
        "prior_disputes_count": dispute_input.get("prior_disputes_count"),
        "prior_refunds_count": dispute_input.get("prior_refunds_count"),
        "days_to_dispute": dispute_input.get("days_to_dispute"),
        "customer_contact_data": dispute_input.get("customer_contact_data", {}),
        "order_velocity_flag": dispute_input.get("order_velocity_flag", False),
        "card_fingerprint": dispute_input.get("card_fingerprint"),
        "customer_email": dispute_input.get("customer_email"),
        "customer_name": dispute_input.get("customer_name"),
        "dispute_filed_timestamp": dispute_input.get("dispute_filed_timestamp"),
        "charge_created_timestamp": dispute_input.get("charge_created_timestamp"),
    }

    user_content = json.dumps(behavior_slice, indent=2)

    try:
        raw = await _call_claude(BEHAVIOR_PROMPT, user_content)
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "behavior_pattern": None,
            "prior_orders_count": None,
            "prior_disputes_count": None,
            "prior_refunds_count": None,
            "days_to_dispute": None,
            "timeline_classification": None,
            "pre_dispute_customer_contact": None,
            "order_velocity_flag": False,
            "friendly_fraud_indicators": [],
            "true_fraud_indicators": [],
            "behavior_score": None,
            "missing_evidence": ["behavior_analysis parse error - all fields null"],
            "parse_error": True,
        }


async def analyze_transaction_risk(dispute_input: dict) -> dict:
    """Call 3 (parallel): evaluate authentication and risk signals."""
    refund_before_dispute = bool(dispute_input.get("refund_history"))

    risk_slice = {
        "dispute_category": dispute_input.get("dispute_category"),
        "dispute_amount": dispute_input.get("dispute_amount"),
        "eci_indicator": dispute_input.get("eci_indicator"),
        "wallet_type": dispute_input.get("wallet_type"),
        "avs_result": dispute_input.get("avs_result"),
        "cvc_result": dispute_input.get("cvc_result"),
        "three_d_secure": dispute_input.get("three_d_secure", {}),
        "radar_score": dispute_input.get("radar_score"),
        "radar_risk_level": dispute_input.get("radar_risk_level"),
        "card_funding_type": dispute_input.get("card_funding_type"),
        "card_country": dispute_input.get("card_country"),
        "refund_history": dispute_input.get("refund_history", []),
        "dispute_filed_timestamp": dispute_input.get("dispute_filed_timestamp"),
        "refund_before_dispute": refund_before_dispute,
    }

    user_content = json.dumps(risk_slice, indent=2)

    try:
        raw = await _call_claude(TRANSACTION_RISK_PROMPT, user_content)
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "authentication_strength": None,
            "eci_indicator": None,
            "wallet_type": None,
            "avs_result": None,
            "avs_interpretation": None,
            "cvc_result": None,
            "cvc_interpretation": None,
            "radar_score": None,
            "radar_risk_level": None,
            "card_funding_type": None,
            "refund_before_dispute": None,
            "refund_in_flight_flag": False,
            "overall_risk_score": None,
            "anomaly_flags": [],
            "strong_signals": [],
            "missing_evidence": ["transaction_risk_analysis parse error - all fields null"],
            "parse_error": True,
        }


async def analyze_reason_code(dispute_input: dict) -> dict:
    """Call 4 (parallel): translate reason code and check CE3 eligibility."""
    delivery_status = dispute_input.get("delivery_status", {})
    delivery_summary = {
        "delivery_confirmed": delivery_status.get("delivery_confirmed"),
        "current_status": delivery_status.get("current_status"),
    }

    reason_slice = {
        "dispute_category": dispute_input.get("dispute_category"),
        "network_reason_code": dispute_input.get("network_reason_code"),
        "card_network": dispute_input.get("card_network"),
        "dispute_amount": dispute_input.get("dispute_amount"),
        "prior_orders_count": dispute_input.get("prior_orders_count"),
        "eci_indicator": dispute_input.get("eci_indicator"),
        "avs_result": dispute_input.get("avs_result"),
        "days_to_dispute": dispute_input.get("days_to_dispute"),
        "delivery_summary": delivery_summary,
        "visa_ce3_eligibility": dispute_input.get("visa_ce3_eligibility"),
        "card_fingerprint": dispute_input.get("card_fingerprint"),
    }

    user_content = json.dumps(reason_slice, indent=2)

    try:
        raw = await _call_claude(REASON_CODE_PROMPT, user_content)
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "reason_code": None,
            "card_network": None,
            "plain_english_translation": None,
            "coherence_assessment": None,
            "coherence_explanation": None,
            "recommended_pipeline": "general_ambiguous",
            "visa_ce3_eligibility": "not_applicable",
            "visa_ce3_qualifying_transactions": None,
            "misapplication_flag": False,
            "misapplication_note": None,
            "missing_evidence": ["reason_code_analysis parse error - all fields null"],
            "parse_error": True,
        }


async def synthesize(
    dispute_input: dict,
    evidence: dict,
    revision_instructions: list | None = None,
) -> str:
    """Call 5: synthesize all four parallel outputs into a final report.

    Returns the raw XML string. Caller handles parsing so the raw text
    is always available if synthesis produces malformed XML.
    """
    synthesis_input = {
        "delivery_analysis": evidence.get("delivery_analysis", {}),
        "behavior_analysis": evidence.get("behavior_analysis", {}),
        "transaction_risk": evidence.get("transaction_risk", {}),
        "reason_code_analysis": evidence.get("reason_code_analysis", {}),
        "merchant_context": dispute_input.get("merchant_context", {}),
        "uploaded_documents": dispute_input.get("uploaded_documents", []),
    }

    user_content = json.dumps(synthesis_input, indent=2)

    if revision_instructions:
        revision_block = (
            "\n\n<revision_required>\n"
            "The following issues were identified in your previous report. "
            "Fix all of them before returning a revised report.\n\n"
            + json.dumps(revision_instructions, indent=2)
            + "\n</revision_required>"
        )
        user_content = user_content + revision_block

    return await _call_claude(SYNTHESIS_PROMPT, user_content)


async def evaluate_report(report_xml: str, dispute_input: dict) -> dict:
    """Call 6: validate the synthesis report against 9 quality criteria."""
    routing = dispute_input.get("_routing", {})
    recommended_pipeline = routing.get("pipeline", "unknown")

    user_content = (
        f"<dispute_context>\n"
        f"dispute_amount: {dispute_input.get('dispute_amount')}\n"
        f"recommended_pipeline: {recommended_pipeline}\n"
        f"</dispute_context>\n\n"
        f"<report_to_evaluate>\n{report_xml}\n</report_to_evaluate>"
    )

    try:
        raw = await _call_claude(EVALUATOR_PROMPT, user_content)
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "overall_result": "revision_required",
            "criteria_results": {},
            "failed_criteria": ["evaluator_parse_error"],
            "revision_instructions": [
                {
                    "criterion": "evaluator_parse_error",
                    "issue": "Evaluator returned unparseable JSON.",
                    "required_fix": "Ensure the report follows all output format requirements.",
                }
            ],
            "approved_for_delivery": False,
            "parse_error": True,
        }


async def analyze_dispute(dispute_input: dict) -> dict:
    """Main entry point. Runs all seven calls in the correct order.

    Returns a dict with the final report, routing decision, evidence
    from all four parallel calls, evaluator output, loop count, and
    flags for low confidence and parse errors.
    """
    # Call 0: Route - must complete before parallel calls start.
    # Stash result under underscore key to signal injected state.
    routing = await route_dispute(dispute_input)
    dispute_input["_routing"] = routing

    # Calls 1-4: Four parallel evidence evaluations.
    # asyncio.gather fires all four simultaneously - same pattern as
    # running card network rules and an ML model at the same time.
    delivery_result, behavior_result, risk_result, reason_code_result = await asyncio.gather(
        analyze_delivery(dispute_input),
        analyze_behavior(dispute_input),
        analyze_transaction_risk(dispute_input),
        analyze_reason_code(dispute_input),
    )

    evidence = {
        "delivery_analysis": delivery_result,
        "behavior_analysis": behavior_result,
        "transaction_risk": risk_result,
        "reason_code_analysis": reason_code_result,
    }

    # Call 5: Initial synthesis.
    report_xml = await synthesize(dispute_input, evidence)

    # Evaluator-Optimizer loop (Call 6). Validates synthesis output against
    # nine quality criteria. Loops with revision instructions if it fails.
    # Backtesting a fraud rule before deploying it - validate before commit.
    loop_count = 0
    low_confidence_flag = False
    evaluation = None
    any_parse_error = any(
        r.get("parse_error")
        for r in [routing, delivery_result, behavior_result, risk_result, reason_code_result]
        if isinstance(r, dict)
    )

    while loop_count < MAX_EVALUATOR_LOOPS:
        evaluation = await evaluate_report(report_xml, dispute_input)
        loop_count += 1

        if evaluation.get("overall_result") == "approved":
            break

        if loop_count < MAX_EVALUATOR_LOOPS:
            revision_instructions = evaluation.get("revision_instructions", [])
            report_xml = await synthesize(dispute_input, evidence, revision_instructions)
        else:
            # Loop exhausted without approval. Append flag and deliver best effort.
            low_confidence_flag = True
            report_xml = report_xml + (
                "\n\n<!-- LOW_CONFIDENCE_FLAG: Report could not be fully validated "
                "after 3 evaluator iterations. Manual review recommended. -->"
            )
            break

    return {
        "report_xml": report_xml,
        "routing": routing,
        "evidence": evidence,
        "evaluation": evaluation,
        "loop_count": loop_count,
        "low_confidence_flag": low_confidence_flag,
        "parse_error": any_parse_error,
    }
