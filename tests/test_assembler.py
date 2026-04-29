"""Tests for assembler.py - dispute input data assembly layer."""

import pytest
import stripe
from unittest.mock import MagicMock, patch

from retina.assembler import (
    _build_customer_history,
    _combine_avs,
    assemble_dispute_input,
)

# ---------------------------------------------------------------------------
# Pure unit tests - no Stripe, no network
# ---------------------------------------------------------------------------


def test_combine_avs_full_match():
    assert _combine_avs("pass", "pass") == "Y"


def test_combine_avs_address_only_fail_postal():
    assert _combine_avs("pass", "fail") == "A"


def test_combine_avs_address_only_unavailable_postal():
    assert _combine_avs("pass", "unavailable") == "A"


def test_combine_avs_postal_only_fail_address():
    assert _combine_avs("fail", "pass") == "Z"


def test_combine_avs_postal_only_unavailable_address():
    assert _combine_avs("unavailable", "pass") == "Z"


def test_combine_avs_no_match():
    assert _combine_avs("fail", "fail") == "N"


def test_combine_avs_both_unavailable():
    assert _combine_avs("unavailable", "unavailable") is None


def test_combine_avs_none_inputs():
    assert _combine_avs(None, None) is None


# ---------------------------------------------------------------------------
# _build_customer_history unit tests
# ---------------------------------------------------------------------------


def _charge(charge_id, created, disputed=False, amount_refunded=0):
    c = MagicMock()
    c.id = charge_id
    c.created = created
    c.disputed = disputed
    c.amount_refunded = amount_refunded
    c.refunded = amount_refunded > 0
    return c


def test_build_customer_history_basic_counts():
    charges = [
        _charge("ch_0", 1710000000),
        _charge("ch_1", 1709913600, disputed=True),
        _charge("ch_2", 1709827200, amount_refunded=500),
        _charge("ch_3", 1709740800),
        _charge("ch_4", 1709654400),
    ]
    result = _build_customer_history(charges, "ch_disputed", 1710100000)
    assert result["prior_orders_count"] == 5
    assert result["prior_disputes_count"] == 1
    assert result["prior_refunds_count"] == 1


def test_build_customer_history_excludes_disputed_charge():
    charges = [
        _charge("ch_0", 1710000000),
        _charge("ch_disputed", 1709913600),
        _charge("ch_2", 1709827200),
    ]
    result = _build_customer_history(charges, "ch_disputed", 1710100000)
    assert result["prior_orders_count"] == 2


def test_build_customer_history_velocity_flag_triggers():
    base_ts = 1710086400
    charges = [
        _charge("ch_0", base_ts - 86400),
        _charge("ch_1", base_ts - 5 * 86400),
        _charge("ch_2", base_ts - 10 * 86400),
    ]
    result = _build_customer_history(charges, "ch_x", base_ts)
    assert result["order_velocity_flag"] is True


def test_build_customer_history_velocity_flag_not_triggered():
    base_ts = 1710086400
    charges = [
        _charge("ch_0", base_ts - 86400),
        _charge("ch_1", base_ts - 5 * 86400),
    ]
    result = _build_customer_history(charges, "ch_x", base_ts)
    assert result["order_velocity_flag"] is False


def test_build_customer_history_old_charges_outside_velocity_window():
    base_ts = 1710086400
    charges = [
        _charge("ch_0", base_ts - 5 * 86400),
        _charge("ch_1", base_ts - 45 * 86400),
        _charge("ch_2", base_ts - 90 * 86400),
    ]
    result = _build_customer_history(charges, "ch_x", base_ts)
    assert result["order_velocity_flag"] is False


# ---------------------------------------------------------------------------
# Helpers shared by mocked async tests
# ---------------------------------------------------------------------------


def _make_mock_dispute():
    """Build a minimal but structurally correct mock Stripe dispute object."""
    d = MagicMock()
    d.reason = "fraudulent"
    d.amount = 5000
    d.currency = "usd"
    d.status = "needs_response"
    d.created = 1710086400  # 2024-03-11 00:00 UTC
    d.is_charge_refundable = True
    d.balance_transactions = []

    d.payment_method_details.card.network_reason_code = "10.4"
    d.payment_method_details.card.case_type = "chargeback"

    d.evidence_details.due_by = 1712764800
    vce3 = d.evidence_details.enhanced_eligibility.visa_compelling_evidence_3
    vce3.status = "not_qualified"
    vce3.required_actions = []

    c = d.charge
    c.id = "ch_test123"
    c.created = 1709913600  # 2024-03-08 -> 2 days before dispute
    c.receipt_email = "customer@example.com"
    c.customer = None  # guest checkout - triggers fingerprint fallback path

    c.billing_details.name = "Jane Smith"
    c.billing_details.email = "customer@example.com"
    c.billing_details.address.line1 = "123 Main St"
    c.billing_details.address.line2 = None
    c.billing_details.address.city = "Austin"
    c.billing_details.address.state = "TX"
    c.billing_details.address.postal_code = "78701"
    c.billing_details.address.country = "US"

    pmc = c.payment_method_details.card
    pmc.brand = "visa"
    pmc.fingerprint = "fp_test123"
    pmc.funding = "credit"
    pmc.country = "US"
    pmc.last4 = "4242"
    pmc.three_d_secure = None
    pmc.wallet = None
    pmc.network_token = None
    pmc.checks.address_line1_check = "pass"
    pmc.checks.address_postal_code_check = "pass"
    pmc.checks.cvc_check = "pass"

    c.outcome.risk_score = 15
    c.outcome.risk_level = "normal"
    c.outcome.rule = None
    c.outcome.seller_message = "Payment complete"

    c.radar_options.session = None
    c.fraud_details.stripe_report = None
    c.fraud_details.user_report = None
    c.refunds.data = []

    return d


def _make_empty_charges_page():
    page = MagicMock()
    page.data = []
    return page


# ---------------------------------------------------------------------------
# Mocked async tests - no real Stripe calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_form_fields_produce_none_not_key_error():
    """Empty form_data must yield None for all optional form fields."""
    with (
        patch("stripe.Dispute.retrieve", return_value=_make_mock_dispute()),
        patch("stripe.Charge.list", return_value=_make_empty_charges_page()),
    ):
        result = await assemble_dispute_input("dp_test", {}, [])

    assert result["fulfillment_data"]["tracking_number"] is None
    assert result["fulfillment_data"]["carrier"] is None
    assert result["fulfillment_data"]["ship_date"] is None
    assert result["fulfillment_data"]["delivery_date"] is None
    assert result["fulfillment_data"]["delivery_confirmation_status"] is None
    assert result["fulfillment_data"]["billing_address_matched_shipping"] is None
    assert result["merchant_context"]["dispute_rate"] is None
    assert result["merchant_context"]["billing_descriptor"] is None
    assert result["merchant_context"]["risk_posture"] == "unknown"


@pytest.mark.asyncio
async def test_all_required_top_level_keys_present():
    """Return dict must contain every key that analyze_dispute() reads."""
    with (
        patch("stripe.Dispute.retrieve", return_value=_make_mock_dispute()),
        patch("stripe.Charge.list", return_value=_make_empty_charges_page()),
    ):
        result = await assemble_dispute_input("dp_test", {}, [])

    required_keys = [
        "dispute_id",
        "dispute_category",
        "network_reason_code",
        "card_network",
        "dispute_amount",
        "dispute_currency",
        "evidence_due_by",
        "dispute_status",
        "case_type",
        "visa_ce3_eligibility",
        "visa_ce3_required_actions",
        "is_charge_refundable",
        "balance_transactions",
        "dispute_filed_timestamp",
        "customer_name",
        "customer_email",
        "receipt_email",
        "customer_billing_address",
        "eci_indicator",
        "wallet_type",
        "card_fingerprint",
        "avs_result",
        "cvc_result",
        "three_d_secure",
        "card_funding_type",
        "card_country",
        "card_last4",
        "network_token_used",
        "radar_score",
        "radar_risk_level",
        "radar_rule",
        "seller_message",
        "radar_session_id",
        "fraud_details",
        "refund_history",
        "charge_created_timestamp",
        "days_to_dispute",
        "prior_orders_count",
        "prior_disputes_count",
        "prior_refunds_count",
        "order_velocity_flag",
        "delivery_status",
        "fulfillment_data",
        "customer_contact_data",
        "merchant_context",
        "uploaded_documents",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_dispute_fields_correctly_mapped():
    """Spot-check that Layer 1 dispute fields land on the right dict keys."""
    with (
        patch("stripe.Dispute.retrieve", return_value=_make_mock_dispute()),
        patch("stripe.Charge.list", return_value=_make_empty_charges_page()),
    ):
        result = await assemble_dispute_input("dp_test", {}, [])

    assert result["dispute_category"] == "fraudulent"
    assert result["dispute_amount"] == 5000
    assert result["dispute_currency"] == "usd"
    assert result["network_reason_code"] == "10.4"
    assert result["case_type"] == "chargeback"
    assert result["dispute_id"] == "dp_test"


@pytest.mark.asyncio
async def test_charge_expansion_fields_correctly_mapped():
    """Spot-check that Layer 2 charge expansion fields land on the right dict keys."""
    with (
        patch("stripe.Dispute.retrieve", return_value=_make_mock_dispute()),
        patch("stripe.Charge.list", return_value=_make_empty_charges_page()),
    ):
        result = await assemble_dispute_input("dp_test", {}, [])

    assert result["card_network"] == "Visa"
    assert result["card_fingerprint"] == "fp_test123"
    assert result["avs_result"] == "Y"
    assert result["cvc_result"] == "pass"
    assert result["radar_score"] == 15
    assert result["radar_risk_level"] == "normal"
    assert result["wallet_type"] == "standard"
    assert result["three_d_secure"] == {}
    assert result["eci_indicator"] is None
    assert result["seller_message"] == "Payment complete"
    assert result["refund_history"] == []
    assert result["fraud_details"] == {"stripe_report": None, "user_report": None}


@pytest.mark.asyncio
async def test_days_to_dispute_calculated_correctly():
    """days_to_dispute must be floor((dispute.created - charge.created) / 86400)."""
    with (
        patch("stripe.Dispute.retrieve", return_value=_make_mock_dispute()),
        patch("stripe.Charge.list", return_value=_make_empty_charges_page()),
    ):
        result = await assemble_dispute_input("dp_test", {}, [])

    # 1710086400 - 1709913600 = 172800 seconds = 2 days exactly
    assert result["days_to_dispute"] == 2


@pytest.mark.asyncio
async def test_invalid_dispute_id_raises_value_error():
    """A dispute ID not found in Stripe must raise ValueError with a clear message."""
    exc = stripe.error.InvalidRequestError("No such dispute: dp_x", "id")
    with patch("stripe.Dispute.retrieve", side_effect=exc):
        with pytest.raises(ValueError, match="not found"):
            await assemble_dispute_input("dp_doesnotexist", {}, [])


# ---------------------------------------------------------------------------
# Integration tests - require STRIPE_API_KEY in environment
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_assemble_integration_returns_populated_dict():
    """Full assemble against the sandbox dispute ID current as of Phase 6B.

    Run with:
        .venv\\Scripts\\python.exe -m pytest tests/test_assembler.py -k integration -v -s
    """
    import os
    import stripe as real_stripe

    stripe_key = os.environ.get("STRIPE_API_KEY")
    if not stripe_key:
        pytest.skip("STRIPE_API_KEY not set")

    real_stripe.api_key = stripe_key

    dispute_id = "du_1TRZTZ0BuWfcB30elCv2VEn5"
    result = await assemble_dispute_input(dispute_id, {}, [])

    assert "dispute_category" in result
    assert "card_network" in result
    assert "fulfillment_data" in result
    assert "merchant_context" in result
    assert "uploaded_documents" in result

    assert result["dispute_category"] in [
        "fraudulent",
        "product_not_received",
        "product_unacceptable",
        "subscription_canceled",
        "credit_not_processed",
        "duplicate_charge",
        "general",
    ]
    assert isinstance(result["dispute_amount"], int)
    assert result["dispute_amount"] > 0
    assert result["avs_result"] in ("Y", "A", "Z", "N", None)
    assert result["card_network"] in ("Visa", "Mastercard", "Amex", "Discover", "Unknown")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_assemble_integration_customer_history_path_fires():
    """Confirm the customer ID history path ran by checking prior_orders_count is not None.

    A None result means history was unavailable (no customer ID and no fingerprint
    match). A non-None result - even 0 - means the Stripe Charge.list call ran and
    _build_customer_history returned a real count.
    """
    import os
    import stripe as real_stripe

    stripe_key = os.environ.get("STRIPE_API_KEY")
    if not stripe_key:
        pytest.skip("STRIPE_API_KEY not set")

    real_stripe.api_key = stripe_key

    dispute_id = "du_1TRZTZ0BuWfcB30elCv2VEn5"
    result = await assemble_dispute_input(dispute_id, {}, [])

    assert result["prior_orders_count"] is not None, (
        "prior_orders_count is None - customer ID history path did not fire. "
        "Check whether the dispute's charge has a customer object attached."
    )
