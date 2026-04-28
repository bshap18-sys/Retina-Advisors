import asyncio
import json
import os

import pytest
from unittest.mock import AsyncMock, patch

from retina.analyzer import (
    MAX_EVALUATOR_LOOPS,
    analyze_behavior,
    analyze_delivery,
    analyze_dispute,
    analyze_reason_code,
    analyze_transaction_risk,
    evaluate_report,
    route_dispute,
    synthesize,
)

# Skip integration tests unless API key is present in environment.
integration = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set - skipping integration test",
)


def _build_scenario_1_input() -> dict:
    """Scenario 1 from the eval dataset: friendly fraud, high confidence.

    Visa 10.4, $284, ECI 05, Apple Pay, 2 prior orders, 0 prior disputes,
    47 days to dispute, confirmed delivery, no pre-dispute customer contact.
    Expected output: Challenge, High confidence, Friendly fraud.
    """
    return {
        # Layer 1 - Stripe dispute object
        "dispute_id": "du_scenario_1_test",
        "dispute_category": "fraudulent",
        "network_reason_code": "10.4",
        "card_network": "Visa",
        "dispute_amount": 284.00,
        "dispute_filed_timestamp": "2024-05-01T10:00:00Z",
        "evidence_due_date": "2024-05-31",
        "dispute_status": "needs_response",
        "visa_ce3_eligibility": "eligible",
        "is_charge_refundable": True,
        "refund_history": [],
        # Layer 2 - Charge object
        "charge_created_timestamp": "2024-03-15T14:00:00Z",
        "eci_indicator": "05",
        "wallet_type": "apple_pay",
        "avs_result": "Y",
        "cvc_result": "M",
        "three_d_secure": {
            "result": "authenticated",
            "authentication_flow": "frictionless",
            "version": "2.2.0",
        },
        "radar_score": 12,
        "radar_risk_level": "normal",
        "card_funding_type": "credit",
        "card_country": "US",
        "card_fingerprint": "fp_test_scenario_1",
        "network_transaction_id": "ntid_test_001",
        "customer_name": "Jane Smith",
        "customer_email": "jane.smith@email.com",
        "customer_billing_address": {
            "line1": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
            "country": "US",
        },
        # Layer 3 - Customer history
        "prior_orders_count": 2,
        "prior_disputes_count": 0,
        "prior_refunds_count": 0,
        "days_to_dispute": 47,
        # Layer 4 - Delivery MCP output (pre-assembled)
        "delivery_status": {
            "delivery_confirmed": True,
            "delivery_date": "2024-03-18",
            "shipping_address_type": "residential",
            "current_status": "delivered",
            "carrier_events": [
                {
                    "timestamp": "2024-03-18T14:32:00Z",
                    "location": "Austin, TX",
                    "status": "delivered",
                    "description": "Package delivered to front door.",
                }
            ],
        },
        # Layer 5 - Merchant form inputs
        "fulfillment_data": {
            "tracking_number": "DELIVERED-RES-SCN1",
            "carrier": "UPS",
            "ship_date": "2024-03-14",
            "delivery_date": "2024-03-18",
            "delivery_confirmed": True,
            "address_match": True,
        },
        "customer_contact_data": {
            "pre_dispute_customer_contact": False,
            "merchant_contacted_first": False,
            "contact_notes": None,
        },
        "order_context": {
            "product_type": "physical goods",
            "confirmation_email_sent": True,
        },
        "policy_data": {
            "refund_policy_exists": True,
            "policy_shown_at_checkout": True,
        },
        "merchant_context": {
            "dispute_rate": 0.003,
            "risk_posture": "healthy",
            "billing_descriptor": "RETINA ADVISORS",
            "brand_name": "Retina Advisors",
            "mcc": "5999",
        },
        # Layer 6 - Document uploads
        "uploaded_documents": [],
    }


async def test_dispute_input_schema():
    """route_dispute accepts the expected dict structure and returns required keys."""
    minimal_input = {
        "dispute_category": "fraudulent",
        "network_reason_code": "10.4",
        "card_network": "Visa",
        "dispute_amount": 284.00,
        "prior_orders_count": 2,
        "days_to_dispute": 47,
        "eci_indicator": "05",
        "wallet_type": "apple_pay",
        "avs_result": "Y",
        "radar_score": 12,
        "refund_history": [],
        "merchant_context": {
            "billing_descriptor": "RETINA ADVISORS",
            "brand_name": "Retina Advisors",
        },
    }
    mock_response = json.dumps(
        {
            "pipeline": "fraudulent_friendly_fraud",
            "confidence": "high",
            "rationale": "Two prior orders and ECI 05 indicate the legitimate cardholder.",
        }
    )
    with patch("retina.analyzer._call_claude", new=AsyncMock(return_value=mock_response)):
        result = await route_dispute(minimal_input)

    assert "pipeline" in result
    assert "confidence" in result
    assert "rationale" in result


async def test_evaluator_loop_exits_at_max():
    """When evaluate_report always returns revision_required the loop exits at MAX_EVALUATOR_LOOPS."""
    dispute_input = _build_scenario_1_input()

    revision_response = {
        "overall_result": "revision_required",
        "criteria_results": {},
        "failed_criteria": ["structure_completeness"],
        "revision_instructions": [
            {
                "criterion": "structure_completeness",
                "issue": "Missing verdict tag.",
                "required_fix": "Add a verdict tag.",
            }
        ],
        "approved_for_delivery": False,
    }

    with (
        patch(
            "retina.analyzer.route_dispute",
            new=AsyncMock(
                return_value={
                    "pipeline": "fraudulent_friendly_fraud",
                    "confidence": "high",
                    "rationale": "Mock routing.",
                }
            ),
        ),
        patch("retina.analyzer.analyze_delivery", new=AsyncMock(return_value={})),
        patch("retina.analyzer.analyze_behavior", new=AsyncMock(return_value={})),
        patch("retina.analyzer.analyze_transaction_risk", new=AsyncMock(return_value={})),
        patch("retina.analyzer.analyze_reason_code", new=AsyncMock(return_value={})),
        patch("retina.analyzer.synthesize", new=AsyncMock(return_value="<report></report>")),
        patch(
            "retina.analyzer.evaluate_report",
            new=AsyncMock(return_value=revision_response),
        ),
    ):
        result = await analyze_dispute(dispute_input)

    assert result["loop_count"] == MAX_EVALUATOR_LOOPS
    assert result["low_confidence_flag"] is True


async def test_parallel_calls_use_gather():
    """asyncio.gather is called exactly once with exactly four coroutines."""
    dispute_input = _build_scenario_1_input()
    gather_calls = []
    real_gather = asyncio.gather

    async def recording_gather(*coros, **kwargs):
        gather_calls.append(len(coros))
        return await real_gather(*coros, **kwargs)

    with (
        patch(
            "retina.analyzer.route_dispute",
            new=AsyncMock(
                return_value={
                    "pipeline": "fraudulent_friendly_fraud",
                    "confidence": "high",
                    "rationale": "Mock.",
                }
            ),
        ),
        patch("retina.analyzer.analyze_delivery", new=AsyncMock(return_value={})),
        patch("retina.analyzer.analyze_behavior", new=AsyncMock(return_value={})),
        patch("retina.analyzer.analyze_transaction_risk", new=AsyncMock(return_value={})),
        patch("retina.analyzer.analyze_reason_code", new=AsyncMock(return_value={})),
        patch("retina.analyzer.synthesize", new=AsyncMock(return_value="<report></report>")),
        patch(
            "retina.analyzer.evaluate_report",
            new=AsyncMock(
                return_value={
                    "overall_result": "approved",
                    "approved_for_delivery": True,
                }
            ),
        ),
        patch(
            "retina.analyzer.asyncio.gather",
            new=AsyncMock(side_effect=recording_gather),
        ),
    ):
        await analyze_dispute(dispute_input)

    assert len(gather_calls) == 1, "asyncio.gather must be called exactly once"
    assert gather_calls[0] == 4, "asyncio.gather must receive exactly four coroutines"


async def test_json_parse_fallback():
    """analyze_delivery returns the fallback dict when Claude returns non-JSON."""
    bad_response = "Sorry, I cannot analyze this at this time."

    with patch("retina.analyzer._call_claude", new=AsyncMock(return_value=bad_response)):
        result = await analyze_delivery({})

    assert result.get("parse_error") is True
    assert result.get("fulfillment_score") is None
    assert any(
        "delivery_analysis parse error" in str(item) for item in result.get("missing_evidence", [])
    )


async def test_routing_parse_fallback():
    """route_dispute returns general_ambiguous fallback when Claude returns non-JSON."""
    with patch("retina.analyzer._call_claude", new=AsyncMock(return_value="not json")):
        result = await route_dispute({"dispute_category": "fraudulent", "refund_history": []})

    assert result.get("parse_error") is True
    assert result.get("pipeline") == "general_ambiguous"
    assert result.get("confidence") == "low"


@integration
async def test_scenario_1_full_pipeline():
    """Scenario 1: friendly fraud, high confidence. Full seven-call pipeline."""
    dispute_input = _build_scenario_1_input()
    result = await analyze_dispute(dispute_input)

    assert result["report_xml"], "report_xml must not be empty"
    report = result["report_xml"]

    assert "Challenge" in report, f"Verdict must recommend Challenge. Got:\n{report[:500]}"
    assert (
        "Friendly fraud" in report
    ), f"Classification must be Friendly fraud. Got:\n{report[:500]}"
    assert "High" in report, f"Confidence must be High. Got:\n{report[:500]}"
    assert "<evidence_to_submit>" in report, "evidence_to_submit section must be present"

    start = report.find("<evidence_to_submit>") + len("<evidence_to_submit>")
    end = report.find("</evidence_to_submit>")
    assert end > start, "evidence_to_submit closing tag must come after opening tag"
    assert report[start:end].strip(), "evidence_to_submit must have content"

    assert (
        result["routing"]["pipeline"] == "fraudulent_friendly_fraud"
    ), f"Routing must select fraudulent_friendly_fraud. Got: {result['routing']}"
    assert result["low_confidence_flag"] is False, (
        f"Scenario 1 should not exhaust the evaluator loop. loop_count={result['loop_count']}, "
        f"evaluation={result['evaluation']}"
    )


@integration
async def test_scenario_26_evaluator_loop():
    """Scenario 26: evaluator catches a deliberately weak synthesis output.

    Feeds the flawed four-sentence string from the eval dataset directly to
    evaluate_report() and confirms the evaluator returns revision_required
    with all five expected failing criteria identified.
    """
    dispute_input = _build_scenario_1_input()
    dispute_input["_routing"] = {
        "pipeline": "fraudulent_friendly_fraud",
        "confidence": "high",
        "rationale": "Scenario 26 routing stub.",
    }

    flawed_report = (
        "This dispute may potentially be friendly fraud. "
        "The customer has prior orders on this card. "
        "We recommend challenging this dispute. "
        "The merchant's dispute rate is healthy."
    )

    result = await evaluate_report(flawed_report, dispute_input)

    assert (
        result.get("overall_result") == "revision_required"
    ), f"Evaluator must return revision_required for a flawed report. Got: {result}"

    expected_failures = {
        "confidence_justification",
        "two_question_framework",
        "citation_completeness",
        "verdict_format",
        "no_false_confidence",
    }
    failed = set(result.get("failed_criteria", []))
    missing = expected_failures - failed
    assert not missing, f"Evaluator missed required failing criteria: {missing}. Got: {failed}"

    assert result.get(
        "revision_instructions"
    ), "revision_instructions must be non-empty when revision_required"
