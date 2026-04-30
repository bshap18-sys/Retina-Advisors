import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from retina.assembler import assemble_dispute_input
from retina.analyzer import analyze_dispute

app = FastAPI(title="Retina Advisors - Dispute Analyzer")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _parse_header_fields(header_text: Optional[str]) -> dict:
    fields = {"dispute_id": None, "amount": None, "due_date": None, "card_network": None}
    if not header_text:
        return fields
    for line in header_text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        lower = line.lower()
        if lower.startswith("dispute id:"):
            fields["dispute_id"] = line.split(":", 1)[1].strip()
        elif lower.startswith("transaction amount:"):
            fields["amount"] = line.split(":", 1)[1].strip()
        elif lower.startswith("evidence due:"):
            fields["due_date"] = line.split(":", 1)[1].strip()
        elif lower.startswith("card network:"):
            fields["card_network"] = line.split(":", 1)[1].strip()
    return fields


def _parse_metric_cards(cards_text: Optional[str]) -> dict:
    result = {
        "classification": None,
        "winnability": None,
        "dispute_rate_status": None,
        "confidence": None,
    }
    if not cards_text:
        return result
    for line in cards_text.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        # Truncate at " - " only for single-word fields where the model may
        # append qualifiers (e.g. "Low - multiple evidence gaps" -> "Low").
        # classification and dispute_rate_status contain legitimate dashes.
        if key in ("confidence", "winnability"):
            value = value.split(" - ")[0].strip()
        if key in result and value:
            result[key] = value
    return result


def _parse_evidence_items(evidence_text: Optional[str]) -> Optional[list]:
    if not evidence_text:
        return None
    boundaries = [(m.start(), m.group(1)) for m in re.finditer(r"(?m)^\s*(\d+)\.\s", evidence_text)]
    if not boundaries:
        return None
    items = []
    for i, (start, number) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(evidence_text)
        block = evidence_text[start:end].strip()
        block = re.sub(r"^\d+\.\s+", "", block, count=1)
        description_lines: list[str] = []
        source: Optional[str] = None
        weight: Optional[str] = None
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if lower.startswith("source:"):
                source = stripped[7:].strip() or None
            elif lower.startswith("weight:"):
                weight = stripped[7:].strip() or None
            else:
                # Defensive: unrecognized lines become description continuation
                description_lines.append(stripped)
        description = " ".join(description_lines).strip()
        if description:
            items.append(
                {"number": number, "description": description, "source": source, "weight": weight}
            )
    return items or None


def parse_report_xml(xml_string: str) -> dict:
    """Parse synthesis prompt XML into a structured dict for the report template.
    Uses ElementTree with regex fallback for malformed or prose-contaminated XML."""
    text = xml_string.strip()

    # Strip markdown fences that Claude sometimes adds around XML output
    for prefix in ("```xml\n", "```xml", "```\n", "```"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    if text.endswith("```"):
        text = text[:-3].strip()

    # Isolate the <report> block if there is surrounding prose or a LOW_CONFIDENCE comment
    report_start = text.find("<report>")
    report_end = text.rfind("</report>")
    if report_start != -1 and report_end != -1:
        text = text[report_start : report_end + len("</report>")]

    # Try ElementTree first; fall back to per-tag regex on parse failure.
    # Regex fallback handles unescaped HTML characters that appear in analysis prose.
    root = None
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        pass

    def _get(tag: str) -> Optional[str]:
        if root is not None:
            el = root.find(tag)
            if el is not None:
                content = "".join(el.itertext()).strip()
                return content if content else None
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return m.group(1).strip() if m else None

    header_text = _get("dispute_header")
    verdict_text = _get("verdict")
    reason_code_text = _get("reason_code_translation")
    evidence_text = _get("evidence_to_submit")

    if verdict_text is None:
        verdict_action = "unknown"
    else:
        _upper = verdict_text.strip().upper()
        if _upper.startswith("CHALLENGE"):
            verdict_action = "Challenge"
        elif _upper.startswith("ACCEPT"):
            verdict_action = "Accept"
        else:
            verdict_action = "unknown"

    reason_code_misapplication = "does not match" in (reason_code_text or "").lower()

    return {
        "dispute_header": header_text,
        "header_fields": _parse_header_fields(header_text),
        "verdict": verdict_text,
        "verdict_action": verdict_action,
        "metric_cards": _parse_metric_cards(_get("metric_cards")),
        "reason_code_translation": reason_code_text,
        "reason_code_misapplication": reason_code_misapplication,
        "analysis": _get("analysis"),
        "evidence_to_submit": _parse_evidence_items(evidence_text),
        "acceptance_rationale": _get("acceptance_rationale"),
        "data_sources_used": _get("data_sources_used"),
    }


@app.get("/", response_class=HTMLResponse)
async def form_page(request: Request):
    # Starlette 1.0: request is first arg, not embedded in context dict
    return templates.TemplateResponse(request, "form.html")


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    dispute_id: Annotated[str, Form()],
    product_type: Annotated[Optional[str], Form()] = None,
    confirmation_email_sent: Annotated[Optional[str], Form()] = None,
    tracking_number: Annotated[Optional[str], Form()] = None,
    carrier: Annotated[Optional[str], Form()] = None,
    ship_date: Annotated[Optional[str], Form()] = None,
    delivery_date: Annotated[Optional[str], Form()] = None,
    delivery_confirmation_status: Annotated[Optional[str], Form()] = None,
    billing_address_matched_shipping: Annotated[Optional[str], Form()] = None,
    customer_contacted_merchant_before_dispute: Annotated[Optional[str], Form()] = None,
    merchant_contacted_customer_before_dispute: Annotated[Optional[str], Form()] = None,
    contact_notes: Annotated[Optional[str], Form()] = None,
    dispute_rate: Annotated[Optional[str], Form()] = None,
    billing_descriptor: Annotated[Optional[str], Form()] = None,
    mcc: Annotated[Optional[str], Form()] = None,
    risk_posture: Annotated[Optional[str], Form()] = None,
    refund_policy_exists: Annotated[Optional[str], Form()] = None,
    policy_shown_at_checkout: Annotated[Optional[str], Form()] = None,
    files: list[UploadFile] = File(default=[]),
):
    # Convert dispute_rate string to float; ignore unparseable input
    dispute_rate_float: Optional[float] = None
    if dispute_rate:
        try:
            dispute_rate_float = float(dispute_rate)
        except ValueError:
            pass

    # Build form_data dict for assembler
    form_data = {
        "product_type": product_type or None,
        "confirmation_email_sent": confirmation_email_sent or None,
        "tracking_number": tracking_number or None,
        "carrier": carrier or None,
        "ship_date": ship_date or None,
        "delivery_date": delivery_date or None,
        "delivery_confirmation_status": delivery_confirmation_status or None,
        "billing_address_matched_shipping": billing_address_matched_shipping or None,
        "customer_contacted_merchant_before_dispute": customer_contacted_merchant_before_dispute
        or None,
        "merchant_contacted_customer_before_dispute": merchant_contacted_customer_before_dispute
        or None,
        "contact_notes": contact_notes or None,
        "dispute_rate": dispute_rate_float,
        "billing_descriptor": billing_descriptor or None,
        "mcc": mcc or None,
        "risk_posture": risk_posture or "unknown",
        "refund_policy_exists": refund_policy_exists or None,
        "policy_shown_at_checkout": policy_shown_at_checkout or None,
    }

    # Read uploaded files into (filename, bytes) tuples for assembler
    documents: list[tuple[str, bytes]] = []
    if files:
        for upload in files:
            if upload.filename:
                content = await upload.read()
                if content:
                    documents.append((upload.filename, content))

    try:
        dispute_input = await assemble_dispute_input(dispute_id.strip(), form_data, documents)
        result = await analyze_dispute(dispute_input)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "report.html",
            {"error": True, "error_message": str(exc)},
        )

    report = parse_report_xml(result["report_xml"])
    report["low_confidence_flag"] = result["low_confidence_flag"]
    report["loop_count"] = result["loop_count"]

    return templates.TemplateResponse(
        request,
        "report.html",
        {"error": False, "report": report},
    )
