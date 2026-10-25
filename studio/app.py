"""Skills Studio: pick a skill, add a file or paste an email, review the output, approve, export.

Run:  make dev   (or: python -m uvicorn studio.app:app)
Nothing is sent anywhere. Approving only unlocks copy and export for the person at the screen.
"""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agency import config, pdf, services
from evals import run_evals
from studio import console

HERE = Path(__file__).resolve().parent
app = FastAPI(title="Skills Studio", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
UPLOADS = Path(tempfile.mkdtemp(prefix="skills-studio-"))
_files: dict[str, Path] = {}

SKILLS = [
    {"slug": "production-report", "name": "Production report", "icon": "table",
     "blurb": "Weekly spreadsheet in, owner's report out. A script does every sum; Claude explains it."},
    {"slug": "weekly-owner-brief", "name": "Owner brief", "icon": "doc",
     "blurb": "A one-page PDF and an email draft for Monday morning."},
    {"slug": "quote-intake", "name": "Quote intake", "icon": "inbox",
     "blurb": "A messy quote email becomes a clean request, plus what is still missing."},
    {"slug": "customer-reply", "name": "Customer reply", "icon": "chat",
     "blurb": "A reply in the agency's tone, using only the FAQ, with a source for every fact."},
]


def _ctx(request: Request, **kw) -> dict:
    return {"request": request, "demo": config.demo_mode(), "agency": config.AGENCY_NAME, "skills": SKILLS, **kw}


def _page(request: Request, name: str, **kw) -> HTMLResponse:
    return templates.TemplateResponse(request, name, _ctx(request, **kw))


def _week_choices() -> list[dict]:
    return [{"file": p.name, "label": p.stem.replace("production_", "").replace("-W", " week ")}
            for p in reversed(services.sample_weeks())]


async def _workbook(sample: str | None, upload: UploadFile | None) -> tuple[str, Path]:
    """Return (token, path) for an uploaded workbook or a sample week."""
    if upload is not None and upload.filename:
        if not upload.filename.lower().endswith((".xlsx", ".xlsm")):
            raise HTTPException(400, "Please choose an Excel file (.xlsx).")
        token = uuid.uuid4().hex[:12]
        path = UPLOADS / f"{token}.xlsx"
        with open(path, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        _files[token] = path
        return token, path
    names = {p.name: p for p in services.sample_weeks()}
    if sample not in names:
        raise HTTPException(400, "Choose a sample week or add a file.")
    return f"sample:{sample}", names[sample]


def _resolve(token: str) -> Path:
    if token.startswith("sample:"):
        names = {p.name: p for p in services.sample_weeks()}
        if token[7:] in names:
            return names[token[7:]]
    elif token in _files:
        return _files[token]
    raise HTTPException(404, "That file is no longer available. Run the skill again.")


# ---------------------------------------------------------------- pages


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return _page(request, "index.html")


@app.get("/skills/{slug}", response_class=HTMLResponse)
def skill_page(request: Request, slug: str):
    skill = next((s for s in SKILLS if s["slug"] == slug), None)
    if not skill:
        raise HTTPException(404)
    extra = {}
    if slug in ("production-report", "weekly-owner-brief"):
        extra["weeks"] = _week_choices()
    elif slug == "quote-intake":
        extra["samples"] = [p.stem for p in services.sample_emails()]
    else:
        extra["samples"] = [p.stem for p in services.sample_messages()]
    return _page(request, f"{slug.replace('-', '_')}.html", skill=skill, **extra)


@app.get("/sample/{kind}/{name}", response_class=PlainTextResponse)
def sample_text(kind: str, name: str):
    folder = {"quote": services.sample_emails, "message": services.sample_messages}.get(kind)
    if not folder:
        raise HTTPException(404)
    for p in folder():
        if p.stem == name:
            return p.read_text()
    raise HTTPException(404)


# ---------------------------------------------------------------- skill runs (HTMX partials)


@app.post("/run/production-report", response_class=HTMLResponse)
async def run_report(request: Request, sample: str = Form(""), file: UploadFile | None = File(None)):
    try:
        _, path = await _workbook(sample, file)
        out = services.run_report(path)
    except (HTTPException, ValueError) as exc:
        return _page(request, "partials/error.html", message=getattr(exc, "detail", str(exc)))
    return _page(request, "partials/report_result.html", out=out, r=out["report"])


@app.post("/run/weekly-owner-brief", response_class=HTMLResponse)
async def run_brief(request: Request, sample: str = Form(""), file: UploadFile | None = File(None)):
    try:
        token, path = await _workbook(sample, file)
        out = services.run_brief(path)
    except (HTTPException, ValueError) as exc:
        return _page(request, "partials/error.html", message=getattr(exc, "detail", str(exc)))
    pdf_bytes = pdf.render_pdf(out["html"])
    return _page(request, "partials/brief_result.html", out=out, r=out["report"], token=token,
                 pages=pdf.preview_pngs(pdf_bytes), page_count=pdf.page_count(pdf_bytes))


@app.get("/export/brief/{token}")
def export_brief(token: str):
    out = services.run_brief(_resolve(token))
    data = pdf.render_pdf(out["html"])
    name = f"owner_brief_{out['report']['week']}.pdf"
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.post("/run/quote-intake", response_class=HTMLResponse)
def run_intake(request: Request, email: str = Form("")):
    if not email.strip():
        return _page(request, "partials/error.html", message="Paste a quote request email first.")
    out = services.run_intake(email)
    return _page(request, "partials/quote_result.html", out=out, res=out["result"])


@app.post("/run/customer-reply", response_class=HTMLResponse)
def run_reply(request: Request, message: str = Form("")):
    if not message.strip():
        return _page(request, "partials/error.html", message="Paste the customer's email first.")
    out = services.run_reply(message)
    return _page(request, "partials/reply_result.html", out=out, res=out["result"])


# ---------------------------------------------------------------- evals and connector


@app.get("/evals", response_class=HTMLResponse)
def evals_page(request: Request):
    return _page(request, "evals.html")


@app.post("/evals/run", response_class=HTMLResponse)
def evals_run(request: Request):
    return _page(request, "partials/evals_result.html", out=run_evals.run_all())


@app.get("/connector", response_class=HTMLResponse)
def connector_page(request: Request):
    return _page(request, "connector.html", examples=console.EXAMPLES)


@app.post("/connector/ask", response_class=HTMLResponse)
def connector_ask(request: Request, question: str = Form("")):
    if not question.strip():
        return _page(request, "partials/error.html", message="Type a question first.")
    return _page(request, "partials/connector_result.html", out=console.ask(question))


@app.get("/health")
def health():
    return {"ok": True, "demo_mode": config.demo_mode()}
