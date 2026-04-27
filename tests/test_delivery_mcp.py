from retina.delivery_mcp import _build_response

EXPECTED_KEYS = (
    "tracking_number",
    "carrier",
    "delivery_confirmed",
    "delivery_date",
    "shipping_address",
    "shipping_address_type",
    "carrier_events",
    "current_status",
)
ADDRESS_KEYS = ("street", "city", "state", "zip")


def _assert_schema(result: dict, tracking_number: str, carrier: str) -> None:
    for key in EXPECTED_KEYS:
        assert key in result, f"Missing key: {key}"
    for key in ADDRESS_KEYS:
        assert key in result["shipping_address"], f"Missing address key: {key}"
    assert result["tracking_number"] == tracking_number
    assert result["carrier"] == carrier


def test_delivered_residential():
    result = _build_response("DELIVERED-RES-001", "UPS")
    _assert_schema(result, "DELIVERED-RES-001", "UPS")
    assert result["delivery_confirmed"] is True
    assert result["shipping_address_type"] == "residential"
    assert result["current_status"] == "delivered"
    assert result["delivery_date"] == "2024-03-15"
    assert len(result["carrier_events"]) == 3


def test_delivered_commercial():
    result = _build_response("DELIVERED-COM-001", "FedEx")
    _assert_schema(result, "DELIVERED-COM-001", "FedEx")
    assert result["delivery_confirmed"] is True
    assert result["shipping_address_type"] == "commercial"
    assert result["current_status"] == "delivered"
    assert result["delivery_date"] == "2024-03-15"
    assert len(result["carrier_events"]) == 3


def test_delivered_freight_forwarder():
    result = _build_response("DELIVERED-FFW-001", "DHL")
    _assert_schema(result, "DELIVERED-FFW-001", "DHL")
    assert result["delivery_confirmed"] is True
    assert result["shipping_address_type"] == "freight_forwarder"
    assert result["current_status"] == "delivered"
    assert result["delivery_date"] == "2024-03-15"
    assert len(result["carrier_events"]) == 3
    delivered_event = result["carrier_events"][0]
    assert "freight" in delivered_event["description"].lower()


def test_delivered_sameday():
    result = _build_response("DELIVERED-SAMEDAY-001", "UPS")
    _assert_schema(result, "DELIVERED-SAMEDAY-001", "UPS")
    assert result["delivery_confirmed"] is True
    assert result["shipping_address_type"] == "residential"
    assert result["current_status"] == "delivered"
    assert result["delivery_date"] == "2024-03-20"
    assert len(result["carrier_events"]) == 3
    for event in result["carrier_events"]:
        assert event["timestamp"].startswith(
            "2024-03-20"
        ), f"Expected all events on 2024-03-20, got: {event['timestamp']}"
    assert result["carrier_events"][0]["description"] == "Package delivered to front door."


def test_delivered_late():
    result = _build_response("DELIVERED-LATE-001", "USPS")
    _assert_schema(result, "DELIVERED-LATE-001", "USPS")
    assert result["delivery_confirmed"] is True
    assert result["shipping_address_type"] == "residential"
    assert result["current_status"] == "delivered"
    assert result["delivery_date"] == "2024-03-28"
    assert len(result["carrier_events"]) == 5
    earliest = result["carrier_events"][-1]
    latest = result["carrier_events"][0]
    assert earliest["timestamp"].startswith("2024-03-14")
    assert latest["timestamp"].startswith("2024-03-28")


def test_in_transit():
    result = _build_response("INTRANSIT-001", "FedEx")
    _assert_schema(result, "INTRANSIT-001", "FedEx")
    assert result["delivery_confirmed"] is False
    assert result["shipping_address_type"] == "residential"
    assert result["current_status"] == "in_transit"
    assert result["delivery_date"] is None
    assert len(result["carrier_events"]) > 0
    statuses = [e["status"] for e in result["carrier_events"]]
    assert "delivered" not in statuses


def test_exception():
    result = _build_response("EXCEPTION-001", "UPS")
    _assert_schema(result, "EXCEPTION-001", "UPS")
    assert result["delivery_confirmed"] is False
    assert result["shipping_address_type"] == "unknown"
    assert result["current_status"] == "exception"
    assert result["delivery_date"] is None
    assert len(result["carrier_events"]) > 0
    exception_events = [e for e in result["carrier_events"] if e["status"] == "exception"]
    assert len(exception_events) >= 1
    assert "address not found" in exception_events[0]["description"].lower()


def test_default_unknown():
    result = _build_response("UNKNOWN-TRACKING-999", "SomeCarrier")
    _assert_schema(result, "UNKNOWN-TRACKING-999", "SomeCarrier")
    assert result["delivery_confirmed"] is False
    assert result["shipping_address_type"] == "unknown"
    assert result["current_status"] == "unknown"
    assert result["delivery_date"] is None
    assert result["carrier_events"] == []
    for key in ADDRESS_KEYS:
        assert result["shipping_address"][key] == ""


def test_case_insensitive_routing():
    result = _build_response("delivered-res-lowercase", "UPS")
    assert result["delivery_confirmed"] is True
    assert result["shipping_address_type"] == "residential"
    assert result["current_status"] == "delivered"
