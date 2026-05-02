"""Grader for the dispute analyzer eval pipeline.

Two public functions:

    grade_report(report_xml, expected, dispute_input) -> dict
        Hybrid grader. Deterministic layer checks classification, recommendation,
        confidence, key signal presence, and position-sensitive checks.
        Claude quality layer asks whether the reasoning is genuinely expert
        or only superficially correct. Async because of the Claude call.

    grade_scenario_26(evaluator_output) -> dict
        Deterministic only. Checks that the evaluator correctly identified
        the five required failing criteria in the deliberately flawed synthesis
        output. No Claude call - the evaluator output is structured JSON, not
        a reasoning narrative.
"""

import json
import re

from anthropic import AsyncAnthropic

MODEL = "claude-sonnet-4-6"
TEMPERATURE = 0.1

QUALITY_SYSTEM_PROMPT = """\
You are a senior fraud operations reviewer evaluating the quality of a
dispute analysis report produced by an AI fraud analyst.

Your job is to answer one question: does this analysis demonstrate
genuine expert fraud reasoning, or is it only superficially correct?

Superficially correct means the classification and recommendation may
be right, but the reasoning is generic, signals from the actual dispute
data are not cited by name, or the analysis reads as if it could have
been written without examining the specific dispute fields provided.

Expert reasoning means the report cites specific signals from the dispute
data, connects those signals to behavioral implications explicitly, applies
the correct analytical framework for the dispute type, and reaches
conclusions a senior fraud analyst would recognize as well-supported by
the evidence that was actually available.

You will receive the dispute data and the report produced from it.
Evaluate the quality of the reasoning - not just whether the conclusion
is correct. A value is only hallucinated if it does not appear anywhere
in the dispute_data JSON provided - check carefully before flagging.

Return a JSON object only. No prose. No preamble. No explanation outside
the three fields.

{
  "quality_score": integer from 1 to 5,
  "quality_pass": true if score is 4 or above, false otherwise,
  "quality_notes": "one sentence explaining the score"
}

Scoring rubric:
5 - Expert. Specific signals cited throughout, behavioral implications
    stated, correct pipeline applied, conclusions well-supported by the
    evidence in the dispute data.
4 - Strong. Reasoning is sound and grounded in the specific data.
    Minor gaps that do not affect the conclusion.
3 - Adequate. Correct conclusion but reasoning is partially generic or
    misses signals that were available in the dispute data.
2 - Weak. Conclusion may be correct but reasoning is largely generic.
    Signals from the dispute data are missed or not cited.
1 - Poor. Generic analysis that does not engage with the specific dispute
    data, or reasoning contradicts the available evidence.\
"""


def _extract_section(report_xml: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", report_xml, re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_classification(metric_cards: str) -> str:
    match = re.search(r"classification:\s*(.+)", metric_cards, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_confidence(metric_cards: str) -> str:
    match = re.search(r"confidence:\s*(.+)", metric_cards, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_recommendation(verdict: str) -> str:
    if "Challenge" in verdict:
        return "Challenge"
    if "Accept" in verdict:
        return "Accept"
    return ""


def _extract_evidence_lead(evidence_block: str) -> str:
    parts = re.split(r"\n\s*2\.", evidence_block, maxsplit=1)
    return parts[0].strip()


def _check_match(actual: str, expected: str, acceptable: list[str] | None) -> bool:
    if expected in actual:
        return True
    if acceptable:
        return any(alt in actual for alt in acceptable)
    return False


def _signal_str(signal: str | dict) -> str:
    return signal["signal"] if isinstance(signal, dict) else signal


def _check_signal(signal: str | dict, text: str) -> bool:
    if isinstance(signal, dict):
        s = signal["signal"]
        return s.lower() in text.lower() if signal.get("case_insensitive") else s in text
    return signal in text


def _build_quality_slice(dispute_input: dict) -> dict:
    fulfillment = dispute_input.get("fulfillment_data", {})
    contact = dispute_input.get("customer_contact_data", {})
    merchant = dispute_input.get("merchant_context", {})

    quality_slice = {
        "dispute_category": dispute_input.get("dispute_category"),
        "network_reason_code": dispute_input.get("network_reason_code"),
        "dispute_amount": dispute_input.get("dispute_amount", 0) / 100,
        "card_network": dispute_input.get("card_network"),
        "eci_indicator": dispute_input.get("eci_indicator"),
        "avs_result": dispute_input.get("avs_result"),
        "cvc_result": dispute_input.get("cvc_result"),
        "radar_score": dispute_input.get("radar_score"),
        "radar_risk_level": dispute_input.get("radar_risk_level"),
        "prior_orders_count": dispute_input.get("prior_orders_count"),
        "prior_disputes_count": dispute_input.get("prior_disputes_count"),
        "days_to_dispute": dispute_input.get("days_to_dispute"),
        "order_velocity_flag": dispute_input.get("order_velocity_flag"),
        "tracking_number": fulfillment.get("tracking_number"),
        "carrier": fulfillment.get("carrier"),
        "delivery_confirmation_status": fulfillment.get("delivery_confirmation_status"),
        "billing_address_matched_shipping": fulfillment.get("billing_address_matched_shipping"),
        "customer_contacted_merchant_before_dispute": contact.get(
            "customer_contacted_merchant_before_dispute"
        ),
        "contact_notes": contact.get("contact_notes"),
        "product_type": contact.get("product_type"),
        "confirmation_email_sent": contact.get("confirmation_email_sent"),
        "refund_policy_exists": contact.get("refund_policy_exists"),
        "policy_shown_at_checkout": contact.get("policy_shown_at_checkout"),
        "dispute_rate": merchant.get("dispute_rate"),
        "risk_posture": merchant.get("risk_posture"),
        "billing_descriptor": merchant.get("billing_descriptor"),
        "brand_name": merchant.get("brand_name"),
        "mcc": merchant.get("mcc"),
        "uploaded_documents": dispute_input.get("uploaded_documents", []),
        "refund_history": dispute_input.get("refund_history", []),
        "balance_transactions": dispute_input.get("balance_transactions", []),
        "visa_ce3_eligibility": dispute_input.get("visa_ce3_eligibility"),
        "evidence_due_by": dispute_input.get("evidence_due_by"),
    }

    shipping_address_type = fulfillment.get("shipping_address_type")
    if shipping_address_type is not None:
        quality_slice["shipping_address_type"] = shipping_address_type

    return quality_slice


async def _call_quality_check(report_xml: str, dispute_input: dict) -> dict:
    client = AsyncAnthropic()
    quality_slice = _build_quality_slice(dispute_input)

    user_content = (
        f"<dispute_data>\n{json.dumps(quality_slice, indent=2)}\n</dispute_data>\n\n"
        f"<report>\n{report_xml}\n</report>"
    )

    try:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=256,
            temperature=TEMPERATURE,
            system=QUALITY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text.strip())
        return {
            "quality_score": int(parsed.get("quality_score", 1)),
            "quality_pass": bool(parsed.get("quality_pass", False)),
            "quality_notes": str(parsed.get("quality_notes", "")),
        }
    except Exception as exc:
        return {
            "quality_score": 0,
            "quality_pass": False,
            "quality_notes": f"Quality call failed: {exc}",
        }


async def grade_report(
    report_xml: str,
    expected: dict,
    dispute_input: dict,
) -> dict:
    metric_cards = _extract_section(report_xml, "metric_cards")
    verdict = _extract_section(report_xml, "verdict")
    analysis = _extract_section(report_xml, "analysis")
    evidence_block = _extract_section(report_xml, "evidence_to_submit")

    classification_actual = _extract_classification(metric_cards)
    confidence_actual = _extract_confidence(metric_cards)
    recommendation_actual = _extract_recommendation(verdict)
    analysis_first_para = analysis.split("\n\n")[0] if analysis else ""
    evidence_lead = _extract_evidence_lead(evidence_block) if evidence_block else ""

    cls_passed = _check_match(
        classification_actual,
        expected.get("classification", ""),
        expected.get("classification_acceptable"),
    )
    rec_passed = _check_match(
        recommendation_actual,
        expected.get("recommendation", ""),
        expected.get("recommendation_acceptable"),
    )
    conf_passed = _check_match(
        confidence_actual,
        expected.get("confidence", ""),
        expected.get("confidence_acceptable"),
    )

    key_signals = expected.get("key_signals_required", [])
    key_found = [_signal_str(s) for s in key_signals if _check_signal(s, analysis)]
    key_missing = [_signal_str(s) for s in key_signals if not _check_signal(s, analysis)]
    key_passed = not key_missing

    first_para_result = None
    if "first_paragraph_required" in expected:
        tokens = expected["first_paragraph_required"]
        fp_found = [_signal_str(t) for t in tokens if _check_signal(t, analysis_first_para)]
        fp_missing = [_signal_str(t) for t in tokens if not _check_signal(t, analysis_first_para)]
        first_para_result = {
            "passed": not fp_missing,
            "found": fp_found,
            "missing": fp_missing,
        }

    evidence_lead_result = None
    if "evidence_lead_required" in expected:
        tokens = expected["evidence_lead_required"]
        el_found = [_signal_str(t) for t in tokens if _check_signal(t, evidence_lead)]
        el_missing = [_signal_str(t) for t in tokens if not _check_signal(t, evidence_lead)]
        evidence_lead_result = {
            "passed": not el_missing,
            "found": el_found,
            "missing": el_missing,
        }

    layer1_passed = (
        cls_passed
        and rec_passed
        and conf_passed
        and key_passed
        and (first_para_result is None or first_para_result["passed"])
        and (evidence_lead_result is None or evidence_lead_result["passed"])
    )

    layer1: dict = {
        "passed": layer1_passed,
        "classification": {
            "passed": cls_passed,
            "expected": expected.get("classification", ""),
            "actual": classification_actual,
        },
        "recommendation": {
            "passed": rec_passed,
            "expected": expected.get("recommendation", ""),
            "actual": recommendation_actual,
        },
        "confidence": {
            "passed": conf_passed,
            "expected": expected.get("confidence", ""),
            "actual": confidence_actual,
        },
        "key_signals": {
            "passed": key_passed,
            "found": key_found,
            "missing": key_missing,
        },
    }
    if first_para_result is not None:
        layer1["first_paragraph"] = first_para_result
    if evidence_lead_result is not None:
        layer1["evidence_lead"] = evidence_lead_result

    layer2 = await _call_quality_check(report_xml, dispute_input)

    return {
        "passed": layer1_passed and layer2["quality_pass"],
        "layer1": layer1,
        "layer2": layer2,
    }


def grade_scenario_26(evaluator_output: dict) -> dict:
    required_criteria = [
        "confidence_justification",
        "two_question_framework",
        "citation_completeness",
        "verdict_format",
        "no_false_confidence",
    ]

    actual_result = evaluator_output.get("overall_result", "")
    result_passed = actual_result == "revision_required"

    failed_criteria = evaluator_output.get("failed_criteria", [])
    found = [c for c in required_criteria if c in failed_criteria]
    missing = [c for c in required_criteria if c not in failed_criteria]
    criteria_passed = not missing

    return {
        "passed": result_passed and criteria_passed,
        "overall_result": {
            "passed": result_passed,
            "actual": actual_result,
        },
        "failed_criteria": {
            "passed": criteria_passed,
            "required": required_criteria,
            "found": found,
            "missing": missing,
        },
    }
