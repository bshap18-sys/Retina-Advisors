from mcp.server.fastmcp import FastMCP

mcp = FastMCP("delivery-status")


def _build_response(tracking_number: str, carrier: str) -> dict:
    # Routing is case-insensitive. Specific DELIVERED- prefixes checked before
    # shorter ones (alphabetical order: COM, FFW, LATE, RES, SAMEDAY).
    # Temperature 0.1 analogy: deterministic routing, no ambiguity.
    key = tracking_number.upper()

    if key.startswith("DELIVERED-COM"):
        return {
            "tracking_number": tracking_number,
            "carrier": carrier,
            "delivery_confirmed": True,
            "delivery_date": "2024-03-15",
            "shipping_address": {
                "street": "456 Commerce Blvd Ste 200",
                "city": "Dallas",
                "state": "TX",
                "zip": "75201",
            },
            "shipping_address_type": "commercial",
            "carrier_events": [
                {
                    "timestamp": "2024-03-15T11:47:00Z",
                    "location": "Dallas, TX",
                    "status": "delivered",
                    "description": "Package delivered - received by front desk.",
                },
                {
                    "timestamp": "2024-03-15T07:30:00Z",
                    "location": "Dallas, TX",
                    "status": "out_for_delivery",
                    "description": "Package out for delivery.",
                },
                {
                    "timestamp": "2024-03-14T19:55:00Z",
                    "location": "Fort Worth, TX",
                    "status": "in_transit",
                    "description": "Package arrived at carrier facility.",
                },
            ],
            "current_status": "delivered",
        }

    elif key.startswith("DELIVERED-FFW"):
        return {
            "tracking_number": tracking_number,
            "carrier": carrier,
            "delivery_confirmed": True,
            "delivery_date": "2024-03-15",
            "shipping_address": {
                "street": "789 Freight Hub Rd",
                "city": "Miami",
                "state": "FL",
                "zip": "33166",
            },
            "shipping_address_type": "freight_forwarder",
            "carrier_events": [
                {
                    "timestamp": "2024-03-15T10:22:00Z",
                    "location": "Miami, FL",
                    "status": "delivered",
                    "description": "Package received at freight forwarding facility.",
                },
                {
                    "timestamp": "2024-03-15T06:45:00Z",
                    "location": "Miami, FL",
                    "status": "out_for_delivery",
                    "description": "Package out for delivery.",
                },
                {
                    "timestamp": "2024-03-14T21:30:00Z",
                    "location": "Miami, FL",
                    "status": "in_transit",
                    "description": "Package arrived at carrier facility.",
                },
            ],
            "current_status": "delivered",
        }

    elif key.startswith("DELIVERED-LATE"):
        return {
            "tracking_number": tracking_number,
            "carrier": carrier,
            "delivery_confirmed": True,
            "delivery_date": "2024-03-28",
            "shipping_address": {
                "street": "88 Birch Ave",
                "city": "Portland",
                "state": "OR",
                "zip": "97201",
            },
            "shipping_address_type": "residential",
            "carrier_events": [
                {
                    "timestamp": "2024-03-28T16:44:00Z",
                    "location": "Portland, OR",
                    "status": "delivered",
                    "description": "Package delivered to front door.",
                },
                {
                    "timestamp": "2024-03-26T09:11:00Z",
                    "location": "Portland, OR",
                    "status": "out_for_delivery",
                    "description": "Package out for delivery.",
                },
                {
                    "timestamp": "2024-03-22T14:30:00Z",
                    "location": "Seattle, WA",
                    "status": "in_transit",
                    "description": "Package arrived at carrier facility - delayed.",
                },
                {
                    "timestamp": "2024-03-18T07:05:00Z",
                    "location": "Salt Lake City, UT",
                    "status": "in_transit",
                    "description": "Package in transit.",
                },
                {
                    "timestamp": "2024-03-14T11:20:00Z",
                    "location": "Denver, CO",
                    "status": "in_transit",
                    "description": "Package picked up by carrier.",
                },
            ],
            "current_status": "delivered",
        }

    elif key.startswith("DELIVERED-RES"):
        return {
            "tracking_number": tracking_number,
            "carrier": carrier,
            "delivery_confirmed": True,
            "delivery_date": "2024-03-15",
            "shipping_address": {
                "street": "123 Main St",
                "city": "Austin",
                "state": "TX",
                "zip": "78701",
            },
            "shipping_address_type": "residential",
            "carrier_events": [
                {
                    "timestamp": "2024-03-15T14:32:00Z",
                    "location": "Austin, TX",
                    "status": "delivered",
                    "description": "Package delivered to front door.",
                },
                {
                    "timestamp": "2024-03-15T08:14:00Z",
                    "location": "Austin, TX",
                    "status": "out_for_delivery",
                    "description": "Package out for delivery.",
                },
                {
                    "timestamp": "2024-03-14T22:05:00Z",
                    "location": "San Antonio, TX",
                    "status": "in_transit",
                    "description": "Package arrived at carrier facility.",
                },
            ],
            "current_status": "delivered",
        }

    elif key.startswith("DELIVERED-SAMEDAY"):
        # All three events fall on 2024-03-20. This is the timeline signal:
        # dispute filed same day as delivery. Prompt 2 uses this to raise a
        # timeline_flag - cardholder never gave the merchant a chance to respond.
        return {
            "tracking_number": tracking_number,
            "carrier": carrier,
            "delivery_confirmed": True,
            "delivery_date": "2024-03-20",
            "shipping_address": {
                "street": "512 Oak Lane",
                "city": "Nashville",
                "state": "TN",
                "zip": "37201",
            },
            "shipping_address_type": "residential",
            "carrier_events": [
                {
                    "timestamp": "2024-03-20T13:15:00Z",
                    "location": "Nashville, TN",
                    "status": "delivered",
                    "description": "Package delivered to front door.",
                },
                {
                    "timestamp": "2024-03-20T08:50:00Z",
                    "location": "Nashville, TN",
                    "status": "out_for_delivery",
                    "description": "Package out for delivery.",
                },
                {
                    "timestamp": "2024-03-20T03:22:00Z",
                    "location": "Memphis, TN",
                    "status": "in_transit",
                    "description": "Package departed carrier facility.",
                },
            ],
            "current_status": "delivered",
        }

    elif key.startswith("INTRANSIT"):
        return {
            "tracking_number": tracking_number,
            "carrier": carrier,
            "delivery_confirmed": False,
            "delivery_date": None,
            "shipping_address": {
                "street": "301 Maple Dr",
                "city": "Charlotte",
                "state": "NC",
                "zip": "28201",
            },
            "shipping_address_type": "residential",
            "carrier_events": [
                {
                    "timestamp": "2024-03-17T11:33:00Z",
                    "location": "Charlotte, NC",
                    "status": "in_transit",
                    "description": "Package arrived at carrier facility - out for delivery tomorrow.",
                },
                {
                    "timestamp": "2024-03-16T08:20:00Z",
                    "location": "Raleigh, NC",
                    "status": "in_transit",
                    "description": "Package in transit.",
                },
                {
                    "timestamp": "2024-03-15T14:10:00Z",
                    "location": "Richmond, VA",
                    "status": "in_transit",
                    "description": "Package picked up by carrier.",
                },
            ],
            "current_status": "in_transit",
        }

    elif key.startswith("EXCEPTION"):
        return {
            "tracking_number": tracking_number,
            "carrier": carrier,
            "delivery_confirmed": False,
            "delivery_date": None,
            "shipping_address": {
                "street": "999 Unknown Rd",
                "city": "Phoenix",
                "state": "AZ",
                "zip": "85001",
            },
            "shipping_address_type": "unknown",
            "carrier_events": [
                {
                    "timestamp": "2024-03-16T13:45:00Z",
                    "location": "Phoenix, AZ",
                    "status": "exception",
                    "description": "Delivery attempted - address not found.",
                },
                {
                    "timestamp": "2024-03-16T07:00:00Z",
                    "location": "Phoenix, AZ",
                    "status": "out_for_delivery",
                    "description": "Package out for delivery.",
                },
                {
                    "timestamp": "2024-03-15T20:30:00Z",
                    "location": "Tucson, AZ",
                    "status": "in_transit",
                    "description": "Package arrived at carrier facility.",
                },
            ],
            "current_status": "exception",
        }

    else:
        return {
            "tracking_number": tracking_number,
            "carrier": carrier,
            "delivery_confirmed": False,
            "delivery_date": None,
            "shipping_address": {
                "street": "",
                "city": "",
                "state": "",
                "zip": "",
            },
            "shipping_address_type": "unknown",
            "carrier_events": [],
            "current_status": "unknown",
        }


@mcp.tool()
def get_delivery_status(tracking_number: str, carrier: str) -> dict:
    """Look up the delivery status and carrier events for a shipment.

    Returns structured delivery data including confirmation status,
    address type, and a full carrier event timeline. Used by the
    dispute analyzer to assess fulfillment evidence.
    """
    return _build_response(tracking_number, carrier)


if __name__ == "__main__":
    mcp.run()
