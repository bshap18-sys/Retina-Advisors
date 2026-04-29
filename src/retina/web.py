from pathlib import Path
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from retina.assembler import assemble_dispute_input
from retina.analyzer import analyze_dispute

app = FastAPI(title="Retina Advisors - Dispute Analyzer")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


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

    return templates.TemplateResponse(
        request,
        "report.html",
        {"error": False, "dispute_id": dispute_id.strip(), "result": result},
    )
