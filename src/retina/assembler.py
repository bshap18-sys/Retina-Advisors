"""Data assembly layer for the dispute analysis pipeline.

Pulls Stripe data (dispute object, charge expansion, customer history),
looks up delivery status from the local delivery MCP server, pre-processes
uploaded documents via a separate Claude API call, and assembles the
complete dict that analyze_dispute() accepts without modification.

Does NOT call analyze_dispute(). Returns the assembled input dict only.
"""

import asyncio
import base64
import json
import logging
import os
import time
from typing import Any

import stripe
from anthropic import AsyncAnthropic

from retina.delivery_mcp import get_delivery_status as _lookup_delivery_status

logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_API_KEY", "")

MODEL = "claude-sonnet-4-6"
# Temperature 0.1 on document extraction - same rule as the main pipeline.
# Consistent extraction across repeated runs matters here too.
TEMPERATURE = 0.1

# Order velocity: flag if this many or more charges occur within this many
# days before the disputed charge. Both thresholds set in Phase 6B planning.
ORDER_VELOCITY_DAYS = 30
ORDER_VELOCITY_THRESHOLD = 3

# Fingerprint fallback lookback window when no customer ID is available.
FINGERPRINT_LOOKBACK_DAYS = 120

DOCUMENT_EXTRACT_SYSTEM = (
    "You are a document extraction assistant for payment dispute analysis. "
    "Read the provided document and extract key findings relevant to a "
    "payment dispute. Return a JSON object only. No preamble, no prose. "
    "Two fields: document_type (one of: delivery_confirmation, "
    "customer_email, product_photo, invoice, return_policy, other) and "
    "key_findings (a concise string summarizing the most relevant "
    "information for dispute resolution, maximum three sentences)."
)


def _safe_attr(obj: Any, *keys: str, default: Any = None) -> Any:
    """Safely traverse a chain of attribute accesses on Stripe objects.

    Stripe SDK v8 returns typed objects, not dicts. This handles
    AttributeError at any level without crashing the assembler.
    """
    for key in keys:
        if obj is None:
            return default
        try:
            obj = getattr(obj, key, None)
        except Exception:
            return default
    return obj if obj is not None else default


def _combine_avs(address_check: str | None, postal_check: str | None) -> str | None:
    """Map Stripe's two separate AVS checks to a single AVS result code.

    Stripe exposes address_line1_check and address_postal_code_check as
    separate fields. The analysis pipeline expects a single AVS letter code.
    """
    if address_check == "pass" and postal_check == "pass":
        return "Y"
    if address_check == "pass":
        return "A"  # address match, zip mismatch or unavailable
    if postal_check == "pass":
        return "Z"  # zip match, address mismatch or unavailable
    if address_check == "fail" and postal_check == "fail":
        return "N"
    return None


def _build_customer_history(
    charges: list,
    disputed_charge_id: str,
    disputed_charge_created: int,
) -> dict:
    """Derive behavioral history counts from a list of prior charges.

    Excludes the disputed charge itself from all counts. Velocity check
    covers ORDER_VELOCITY_DAYS before the disputed charge's created timestamp.
    """
    prior_orders = 0
    prior_disputes = 0
    prior_refunds = 0
    velocity_window_count = 0
    cutoff = disputed_charge_created - (ORDER_VELOCITY_DAYS * 86400)

    for charge in charges:
        if charge.id == disputed_charge_id:
            continue

        prior_orders += 1

        if getattr(charge, "disputed", False):
            prior_disputes += 1

        if getattr(charge, "amount_refunded", 0) > 0 or getattr(charge, "refunded", False):
            prior_refunds += 1

        if charge.created >= cutoff:
            velocity_window_count += 1

    return {
        "prior_orders_count": prior_orders,
        "prior_disputes_count": prior_disputes,
        "prior_refunds_count": prior_refunds,
        "order_velocity_flag": velocity_window_count >= ORDER_VELOCITY_THRESHOLD,
    }


async def _extract_document_findings(
    client: AsyncAnthropic,
    filename: str,
    file_bytes: bytes,
) -> dict:
    """Pre-process one uploaded document via a Claude API call.

    Returns a dict with document_type and key_findings. Called via
    asyncio.gather so a failure in one file does not affect others.
    """
    encoded = base64.standard_b64encode(file_bytes).decode("utf-8")
    lower = filename.lower()

    if lower.endswith(".pdf"):
        file_block: dict = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": encoded,
            },
        }
    elif lower.endswith(".png"):
        file_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": encoded,
            },
        }
    else:
        file_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": encoded,
            },
        }

    response = await client.messages.create(
        model=MODEL,
        max_tokens=512,
        temperature=TEMPERATURE,
        system=[
            {
                "type": "text",
                "text": DOCUMENT_EXTRACT_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    file_block,
                    {
                        "type": "text",
                        "text": "Extract key findings relevant to a payment dispute.",
                    },
                ],
            }
        ],
    )

    text = response.content[0].text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


async def assemble_dispute_input(
    dispute_id: str,
    form_data: dict,
    documents: list[tuple[str, bytes]],
) -> dict:
    """Assemble the complete dispute_input dict for analyze_dispute().

    Layers assembled:
      1. Stripe dispute object (category, amount, CE3 status, timestamps)
      2. Stripe charge expansion (authentication, card details, Radar, refunds)
      3. Customer history query (prior orders, disputes, velocity flag)
      4. Delivery MCP lookup (delivery status if tracking number provided)
      5. Form inputs (fulfillment data, contact data, merchant context)
      6. Document pre-processing (key findings from uploaded files)

    Raises ValueError if the dispute ID is not found or Stripe returns a
    hard error. Non-fatal failures (charge expansion, delivery lookup,
    document processing) log a warning and continue with None values.
    """
    # Stripe Call 1: retrieve dispute with charge, customer, and refunds
    # expanded in a single round-trip. asyncio.to_thread avoids blocking
    # the event loop with synchronous Stripe SDK calls.
    try:
        dispute = await asyncio.to_thread(
            stripe.Dispute.retrieve,
            dispute_id,
            expand=["charge", "charge.customer", "charge.refunds", "charge.outcome.rule"],
        )
    except stripe.InvalidRequestError as exc:
        raise ValueError(f"Dispute {dispute_id} not found: {exc}") from exc
    except stripe.StripeError as exc:
        raise ValueError(f"Stripe error retrieving dispute {dispute_id}: {exc}") from exc

    # Layer 1 fields from the dispute object
    pmd_dispute_card = _safe_attr(dispute, "payment_method_details", "card", default=None)

    dispute_category = dispute.reason
    dispute_amount = dispute.amount
    dispute_currency = dispute.currency
    dispute_status = dispute.status
    dispute_filed_timestamp = dispute.created
    is_charge_refundable = getattr(dispute, "is_charge_refundable", None)
    balance_transactions = list(getattr(dispute, "balance_transactions", None) or [])

    network_reason_code = _safe_attr(pmd_dispute_card, "network_reason_code")
    case_type = _safe_attr(pmd_dispute_card, "case_type")

    evidence_details = getattr(dispute, "evidence_details", None)
    evidence_due_by = _safe_attr(evidence_details, "due_by")

    # CE3 eligibility and required actions - both nested under enhanced_eligibility
    visa_ce3_eligibility = _safe_attr(
        evidence_details,
        "enhanced_eligibility",
        "visa_compelling_evidence_3",
        "status",
    )
    visa_ce3_required_actions = _safe_attr(
        evidence_details,
        "enhanced_eligibility",
        "visa_compelling_evidence_3",
        "required_actions",
    )

    # Layer 2 fields from the charge expansion
    charge = dispute.charge
    if isinstance(charge, str):
        # Expansion failed - charge is just the ID string, not the full object
        logger.warning(
            "Charge expansion failed for dispute %s - proceeding with partial data",
            dispute_id,
        )
        charge = None

    if charge is not None:
        pmd_charge = getattr(charge, "payment_method_details", None)
        pmd_card = _safe_attr(pmd_charge, "card", default=None)

        # Customer identity - ground truth lives on charge.billing_details,
        # not on dispute.evidence.* which is merchant-supplied and null by default
        billing = getattr(charge, "billing_details", None)
        customer_name = _safe_attr(billing, "name")
        receipt_email = getattr(charge, "receipt_email", None)
        customer_email = _safe_attr(billing, "email") or receipt_email
        billing_addr_obj = _safe_attr(billing, "address")
        customer_billing_address = {
            "line1": _safe_attr(billing_addr_obj, "line1"),
            "line2": _safe_attr(billing_addr_obj, "line2"),
            "city": _safe_attr(billing_addr_obj, "city"),
            "state": _safe_attr(billing_addr_obj, "state"),
            "postal_code": _safe_attr(billing_addr_obj, "postal_code"),
            "country": _safe_attr(billing_addr_obj, "country"),
        }

        # Card network - capitalize for consistency ("visa" -> "Visa")
        raw_brand = _safe_attr(pmd_card, "brand") or "unknown"
        card_network = raw_brand.capitalize()

        # 3DS fields
        tds_obj = _safe_attr(pmd_card, "three_d_secure")
        if tds_obj is not None:
            eci_indicator = _safe_attr(tds_obj, "electronic_commerce_indicator")
            three_d_secure = {
                "result": _safe_attr(tds_obj, "result"),
                "authentication_flow": _safe_attr(tds_obj, "authentication_flow"),
                "version": _safe_attr(tds_obj, "version"),
                "electronic_commerce_indicator": eci_indicator,
                "exemption_indicator": _safe_attr(tds_obj, "exemption_indicator"),
            }
        else:
            eci_indicator = None
            three_d_secure = {}

        # Wallet type: null wallet object = standard card entry
        wallet_obj = _safe_attr(pmd_card, "wallet")
        wallet_type = _safe_attr(wallet_obj, "type") if wallet_obj is not None else "standard"

        card_fingerprint = _safe_attr(pmd_card, "fingerprint")
        card_funding_type = _safe_attr(pmd_card, "funding")
        card_country = _safe_attr(pmd_card, "country")
        card_last4 = _safe_attr(pmd_card, "last4")

        # Network token: CE3-relevant signal
        network_token_used = _safe_attr(pmd_card, "network_token", "used")

        # AVS: Stripe exposes two separate checks, combine into one letter code
        checks_obj = _safe_attr(pmd_card, "checks")
        avs_result = _combine_avs(
            _safe_attr(checks_obj, "address_line1_check"),
            _safe_attr(checks_obj, "address_postal_code_check"),
        )
        cvc_result = _safe_attr(checks_obj, "cvc_check")

        # Radar signals.
        # Known issue (fix in 6E): outcome.rule arrives as a plain string ID in
        # Stripe v8 when the rule object is not expanded. _safe_attr traverses
        # to .id on a string which returns None. Add "charge.outcome.rule" to
        # the expand list in 6E to get the full rule object.
        outcome = getattr(charge, "outcome", None)
        radar_score = _safe_attr(outcome, "risk_score")
        radar_risk_level = _safe_attr(outcome, "risk_level")
        radar_rule = _safe_attr(outcome, "rule", "id")
        seller_message = _safe_attr(outcome, "seller_message")

        # Radar session ID (browser metadata snapshot for identity coherence)
        radar_session_id = _safe_attr(charge, "radar_options", "session")

        # Fraud details: Stripe's own assessment and any prior merchant report
        fd_obj = getattr(charge, "fraud_details", None)
        fraud_details = {
            "stripe_report": _safe_attr(fd_obj, "stripe_report"),
            "user_report": _safe_attr(fd_obj, "user_report"),
        }

        # Refund history with timestamps for refund-in-flight detection
        refunds_obj = getattr(charge, "refunds", None)
        refund_data = getattr(refunds_obj, "data", []) or []
        refund_history = [
            {"id": r.id, "amount": r.amount, "created": r.created} for r in refund_data
        ]

        charge_created_timestamp = charge.created

        # Customer ID for history query - None for guest checkouts
        customer_obj = getattr(charge, "customer", None)
        customer_id = (
            customer_obj if isinstance(customer_obj, str) else _safe_attr(customer_obj, "id")
        )

        charge_id = charge.id

    else:
        # Charge expansion failed - set all charge-level fields to None
        customer_name = None
        receipt_email = None
        customer_email = None
        customer_billing_address = {}
        card_network = "Unknown"
        eci_indicator = None
        three_d_secure = {}
        wallet_type = None
        card_fingerprint = None
        avs_result = None
        cvc_result = None
        card_funding_type = None
        card_country = None
        card_last4 = None
        network_token_used = None
        radar_score = None
        radar_risk_level = None
        radar_rule = None
        seller_message = None
        radar_session_id = None
        fraud_details = {"stripe_report": None, "user_report": None}
        refund_history = []
        charge_created_timestamp = None
        customer_id = None
        charge_id = dispute.charge if isinstance(getattr(dispute, "charge", None), str) else None

    # Derived: days between charge creation and dispute filing
    if charge_created_timestamp and dispute_filed_timestamp:
        days_to_dispute = (dispute_filed_timestamp - charge_created_timestamp) // 86400
    else:
        days_to_dispute = None

    # Layer 3: customer history.
    # Primary path: stripe.Charge.list(customer=customer_id) when customer
    # ID is available (linked customer accounts).
    # Fingerprint fallback: when no customer ID, list recent charges with a
    # 120-day lookback and filter client-side by card fingerprint. Covers
    # guest checkouts where the same card appeared across multiple orders.
    history: dict = {
        "prior_orders_count": None,
        "prior_disputes_count": None,
        "prior_refunds_count": None,
        "order_velocity_flag": False,
    }

    if customer_id:
        try:
            charges_page = await asyncio.to_thread(
                stripe.Charge.list, customer=customer_id, limit=50
            )
            history = _build_customer_history(
                charges_page.data,
                charge_id or "",
                charge_created_timestamp or 0,
            )
        except stripe.StripeError as exc:
            logger.warning(
                "Failed to retrieve customer history for %s (dispute %s): %s",
                customer_id,
                dispute_id,
                exc,
            )
    elif card_fingerprint:
        try:
            lookback_ts = int(time.time()) - (FINGERPRINT_LOOKBACK_DAYS * 86400)
            charges_page = await asyncio.to_thread(
                stripe.Charge.list,
                limit=50,
                created={"gte": lookback_ts},
            )
            matching = [
                c
                for c in charges_page.data
                if _safe_attr(c, "payment_method_details", "card", "fingerprint")
                == card_fingerprint
            ]
            history = _build_customer_history(
                matching,
                charge_id or "",
                charge_created_timestamp or 0,
            )
        except stripe.StripeError as exc:
            logger.warning("Failed fingerprint fallback for dispute %s: %s", dispute_id, exc)
    else:
        logger.warning(
            "No customer ID or fingerprint for dispute %s - customer history unavailable",
            dispute_id,
        )

    # Layer 4: delivery MCP lookup - local Python call, no HTTP overhead
    delivery_status: dict = {}
    tracking_number = form_data.get("tracking_number")
    carrier = form_data.get("carrier")
    if tracking_number and carrier and carrier.lower() not in ("unknown", "other", ""):
        try:
            delivery_status = _lookup_delivery_status(tracking_number, carrier)
        except Exception as exc:
            logger.warning(
                "Delivery MCP lookup failed for %s via %s: %s",
                tracking_number,
                carrier,
                exc,
            )

    # Layer 6: document pre-processing - one Claude call per file via gather
    # so a failed file does not block the others
    uploaded_documents: list = []
    if documents:
        anthropic_client = AsyncAnthropic()
        doc_tasks = [
            _extract_document_findings(anthropic_client, filename, file_bytes)
            for filename, file_bytes in documents
        ]
        results = await asyncio.gather(*doc_tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Document pre-processing failed for file index %d: %s", i, result)
            else:
                uploaded_documents.append(result)

    # Layer 5: form inputs assembled into named sub-dicts.
    # Key names confirmed in Phase 6B planning - must match what the
    # delivery and behavior prompts reference in their slices.
    fulfillment_data = {
        "tracking_number": form_data.get("tracking_number"),
        "carrier": form_data.get("carrier"),
        "ship_date": form_data.get("ship_date"),
        "delivery_date": form_data.get("delivery_date"),
        "delivery_confirmation_status": form_data.get("delivery_confirmation_status"),
        "billing_address_matched_shipping": form_data.get("billing_address_matched_shipping"),
    }

    customer_contact_data = {
        "customer_contacted_merchant_before_dispute": form_data.get(
            "customer_contacted_merchant_before_dispute"
        ),
        "merchant_contacted_customer_before_dispute": form_data.get(
            "merchant_contacted_customer_before_dispute"
        ),
        "contact_notes": form_data.get("contact_notes"),
        "product_type": form_data.get("product_type"),
        "confirmation_email_sent": form_data.get("confirmation_email_sent"),
        "refund_policy_exists": form_data.get("refund_policy_exists"),
        "policy_shown_at_checkout": form_data.get("policy_shown_at_checkout"),
    }

    merchant_context = {
        "dispute_rate": form_data.get("dispute_rate"),
        "risk_posture": form_data.get("risk_posture", "unknown"),
        "billing_descriptor": form_data.get("billing_descriptor"),
        "brand_name": None,  # v2: pull from Stripe account settings
        "mcc": form_data.get("mcc"),
    }

    return {
        # Identifiers
        "dispute_id": dispute_id,
        # Layer 1 - Stripe dispute object
        "dispute_category": dispute_category,
        "network_reason_code": network_reason_code,
        "dispute_amount": dispute_amount,
        "dispute_currency": dispute_currency,
        "evidence_due_by": evidence_due_by,
        "dispute_status": dispute_status,
        "case_type": case_type,
        "visa_ce3_eligibility": visa_ce3_eligibility,
        "visa_ce3_required_actions": visa_ce3_required_actions,
        "is_charge_refundable": is_charge_refundable,
        "balance_transactions": balance_transactions,
        "dispute_filed_timestamp": dispute_filed_timestamp,
        # Layer 2 - Stripe charge expansion
        "card_network": card_network,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "receipt_email": receipt_email,
        "customer_billing_address": customer_billing_address,
        "eci_indicator": eci_indicator,
        "wallet_type": wallet_type,
        "card_fingerprint": card_fingerprint,
        "avs_result": avs_result,
        "cvc_result": cvc_result,
        "three_d_secure": three_d_secure,
        "card_funding_type": card_funding_type,
        "card_country": card_country,
        "card_last4": card_last4,
        "network_token_used": network_token_used,
        "radar_score": radar_score,
        "radar_risk_level": radar_risk_level,
        "radar_rule": radar_rule,
        "seller_message": seller_message,
        "radar_session_id": radar_session_id,
        "fraud_details": fraud_details,
        "refund_history": refund_history,
        "charge_created_timestamp": charge_created_timestamp,
        # Derived from timestamps
        "days_to_dispute": days_to_dispute,
        # Layer 3 - Customer history
        "prior_orders_count": history["prior_orders_count"],
        "prior_disputes_count": history["prior_disputes_count"],
        "prior_refunds_count": history["prior_refunds_count"],
        "order_velocity_flag": history["order_velocity_flag"],
        # Layer 4 - Delivery MCP
        "delivery_status": delivery_status,
        # Layer 5 - Form inputs
        "fulfillment_data": fulfillment_data,
        "customer_contact_data": customer_contact_data,
        "merchant_context": merchant_context,
        # Layer 6 - Document pre-processing
        "uploaded_documents": uploaded_documents,
    }
