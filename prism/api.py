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

from prism.contract import (
    EXAMPLE_RESPONSE,
    PullRequest,
    Signal,
    Signals,
    SnowflakeContext,
    TriageRequest,
    TriageResponse,
)
from prism.context import repo_context
from prism.ingest import fetch_pr
from prism.judge import judge
from prism.signals import extract_signals

load_dotenv()

logger = logging.getLogger("prism.api")

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

# size -> lines_changed (int); the rest are bool flags carried straight through.
SIGNAL_FIELD_MAP = {
    "size": ("lines_changed", int),
    "has_tests": ("has_tests", bool),
    "linked_issue": ("linked_issue", bool),
    "followed_contributing": ("followed_contributing", bool),
}

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


def summarize_signals(signals: list[Signal], ctx: SnowflakeContext) -> Signals:
    values = {"lines_changed": 0, "has_tests": False, "linked_issue": False, "followed_contributing": False}
    for s in signals:
        mapped = SIGNAL_FIELD_MAP.get(s.signal)
        if mapped is None or s.value is None:
            continue
        field, cast = mapped
        try:
            values[field] = cast(s.value)
        except (TypeError, ValueError):
            continue
    return Signals(**values, author_pr_velocity_7d=ctx.author_pr_events_7d)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/triage", response_model=TriageResponse)
def triage(body: TriageRequest) -> TriageResponse:
    try:
        pr = fetch_pr(body.pr_url)
    except NotImplementedError:
        logger.info("stage fetch_pr fell back to mock")
        pr = None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if pr is None:
        # Stand-in PullRequest so downstream stages have something to run against.
        pr = PullRequest(
            url=body.pr_url,
            owner="owner",
            repo="repo",
            number=1,
            title="mock",
            author="mock",
        )

    try:
        signals = extract_signals(pr)
    except NotImplementedError:
        logger.info("stage extract_signals fell back to mock")
        signals = []

    try:
        context = repo_context(pr.author, f"{pr.owner}/{pr.repo}")
    except NotImplementedError:
        logger.info("stage repo_context fell back to mock")
        context = EXAMPLE_RESPONSE.snowflake_context

    try:
        response = judge(pr, signals, context)
    except NotImplementedError:
        logger.info("stage judge fell back to mock")
        response = EXAMPLE_RESPONSE

    summarized = summarize_signals(signals, context)
    return response.model_copy(
        update={
            "pr_url": body.pr_url,
            "signals": summarized,
            "snowflake_context": context,
        }
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")
