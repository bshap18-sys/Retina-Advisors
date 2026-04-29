from retina.web import parse_report_xml

VALID_CHALLENGE_XML = """
<report>

  <dispute_header>
    Dispute ID: dp_test_123
    Transaction amount: $150.00
    Evidence due: 2026-05-15
    Card network: Visa
  </dispute_header>

  <verdict>
    Challenge this dispute - High confidence. This is friendly fraud, not true unauthorized use.
  </verdict>

  <metric_cards>
    classification: Friendly fraud
    winnability: Strong
    dispute_rate_status: Healthy - below 0.5%
    confidence: High
  </metric_cards>

  <reason_code_translation>
    The cardholder told their bank they did not recognize or authorize this charge.
  </reason_code_translation>

  <analysis>
    This dispute shows all hallmarks of friendly fraud. The card fingerprint matches two prior
    undisputed purchases (behavior_analysis), and the dispute was filed 94 days after delivery -
    three days before the dispute window closed (behavior_analysis.timeline_classification:
    calculated).

    The evidence strongly supports challenging this dispute. Delivery was confirmed to the billing
    address (delivery_analysis.fulfillment_score: strong), 3DS authentication was completed
    (transaction_risk.authentication_strength: strong, ECI 05), and the Radar score was 12
    (transaction_risk.radar_risk_level: low).

    The merchant is in a healthy dispute rate position at 0.2% (merchant_context.dispute_rate),
    well below the 0.5% caution threshold. Challenging this dispute is strategically sound and
    consistent with documenting friendly fraud patterns for future deterrence.
  </analysis>

  <evidence_to_submit>
    1. Confirmed delivery to billing address with timestamp proves the item was received.
    Source: Delivery MCP
    Weight: Primary

    2. 3DS full authentication (ECI 05) shifts chargeback liability to the issuing bank.
    Source: Stripe charge payment_method_details.card.three_d_secure
    Weight: Primary

    3. Two prior undisputed purchases on the same card fingerprint within 120 days qualify
    this dispute for Visa Compelling Evidence 3.0 - the strongest available defense.
    Source: Stripe customer history (behavior_analysis)
    Weight: Supporting
  </evidence_to_submit>

  <data_sources_used>
    - Delivery analysis: confirmed delivery to billing address, no timeline flags
    - Behavior analysis: consistent pattern, calculated timeline, two prior orders
    - Transaction risk analysis: strong 3DS authentication, low Radar score
    - Reason code analysis: coherent with friendly fraud pipeline
    - Merchant context: dispute rate 0.2%, healthy posture
    - Uploaded documents: none
    - Not available: purchase IP
  </data_sources_used>

</report>
"""

VALID_ACCEPT_XML = """
<report>

  <dispute_header>
    Dispute ID: dp_test_456
    Transaction amount: $25.00
    Evidence due: 2026-05-20
    Card network: Mastercard
  </dispute_header>

  <verdict>
    Accept this dispute - Low confidence. This is a weak case, not a winnable challenge.
  </verdict>

  <metric_cards>
    classification: Genuine fulfillment failure
    winnability: Weak
    dispute_rate_status: Triage - above 0.5% and climbing
    confidence: Low
  </metric_cards>

  <reason_code_translation>
    The cardholder claims they never received their order.
  </reason_code_translation>

  <analysis>
    No delivery confirmation is available for this dispute. Without tracking proof of delivery,
    this case has weak winnability regardless of other signals (delivery_analysis.fulfillment_score:
    weak, delivery_analysis.delivery_confirmed: false).

    This dispute involves a $25.00 transaction. Fighting and losing costs $30 in Stripe fees.
    Fighting and winning costs $15. Accepting costs $15. The fee math makes challenging
    irrational even if the case were stronger.

    The merchant is in triage mode at 0.7% dispute rate (merchant_context.dispute_rate),
    above the 0.5% caution threshold. Accepting this dispute protects the dispute rate
    and avoids the $30 counter-dispute fee on a $25 transaction.
  </analysis>

  <acceptance_rationale>
    Accepting this dispute avoids a $30 counter-dispute fee on a $25 transaction and
    protects the merchant's dispute rate during a critical triage period. This is a
    deliberate strategic decision to preserve rate headroom, not a concession on the merits.
  </acceptance_rationale>

  <data_sources_used>
    - Delivery analysis: no delivery confirmation, tracking number not provided
    - Behavior analysis: insufficient history
    - Transaction risk analysis: no 3DS, Radar score 41 (moderate)
    - Reason code analysis: coherent with product_not_received pipeline
    - Merchant context: dispute rate 0.7%, triage posture
    - Uploaded documents: none
    - Not available: tracking number, delivery confirmation, customer contact record
  </data_sources_used>

</report>
"""

MALFORMED_XML = """
<report>

  <dispute_header>
    Dispute ID: dp_test_789
    Transaction amount: $200.00
  </dispute_header>

  <verdict>
    Challenge this dispute - Medium confidence. This is friendly fraud.

  <metric_cards>
    classification: Friendly fraud
    winnability: Moderate
    confidence: Medium
  </metric_cards>

  <analysis>
    Evidence supports a challenge but is incomplete.
  </analysis>

</report>
"""


def test_parse_challenge_report():
    result = parse_report_xml(VALID_CHALLENGE_XML)

    assert result["verdict_action"] == "Challenge"
    assert result["header_fields"]["dispute_id"] == "dp_test_123"
    assert result["header_fields"]["amount"] == "$150.00"
    assert result["header_fields"]["card_network"] == "Visa"
    assert result["metric_cards"]["classification"] == "Friendly fraud"
    assert result["metric_cards"]["winnability"] == "Strong"
    assert result["metric_cards"]["confidence"] == "High"

    items = result["evidence_to_submit"]
    assert items is not None
    assert len(items) == 3
    assert items[0]["number"] == "1"
    assert items[0]["weight"] == "Primary"
    assert items[2]["weight"] == "Supporting"
    assert items[0]["source"] == "Delivery MCP"

    assert result["acceptance_rationale"] is None
    assert result["reason_code_misapplication"] is False


def test_parse_accept_report():
    result = parse_report_xml(VALID_ACCEPT_XML)

    assert result["verdict_action"] == "Accept"
    assert result["header_fields"]["dispute_id"] == "dp_test_456"
    assert result["metric_cards"]["winnability"] == "Weak"
    assert result["metric_cards"]["dispute_rate_status"] == "Triage - above 0.5% and climbing"

    assert result["evidence_to_submit"] is None
    assert result["acceptance_rationale"] is not None
    assert "triage" in result["acceptance_rationale"].lower()


def test_parse_malformed_xml_does_not_raise():
    result = parse_report_xml(MALFORMED_XML)

    assert isinstance(result, dict)
    assert "verdict_action" in result
    assert "metric_cards" in result
    assert result["metric_cards"]["classification"] == "Friendly fraud"
    # Missing verdict closing tag - verdict_action falls back gracefully
    assert result["verdict_action"] in ("Challenge", "Accept", "unknown")
    # Missing tags return None without raising
    assert result["data_sources_used"] is None
    assert result["evidence_to_submit"] is None
