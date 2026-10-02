"""HTTP API. Rohith owns this file."""

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from prism.contract import TriageRequest, TriageResponse
from prism.context import repo_context
from prism.ingest import IngestError, fetch_pr
from prism.judge import judge
from prism.signals import extract_signals

load_dotenv()

logger = logging.getLogger("prism.api")

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

app = FastAPI(title="PRism")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    messages = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
    return JSONResponse(status_code=422, content={"error": messages})


@app.exception_handler(StarletteHTTPException)
def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error in %s", request.url.path)
    return JSONResponse(status_code=500, content={"error": "Internal server error."})


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/triage", response_model=TriageResponse)
def triage(body: TriageRequest) -> TriageResponse:
    try:
        pr = fetch_pr(body.pr_url)
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    signals = extract_signals(pr)
    context = repo_context(pr.author, f"{pr.owner}/{pr.repo}")
    try:
        return judge(pr, signals, context)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")
