from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Retina Advisors - Dispute Analyzer")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def form_page(request: Request):
    # Starlette 1.0: request is first arg, not embedded in context dict
    return templates.TemplateResponse(request, "form.html")
