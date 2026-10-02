"""HTTP API. Rohith owns this file.

The route and the mock response are wired so the UI can run before the
pipeline exists. Replace the mock return with the four calls below.
"""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from prism.contract import EXAMPLE_RESPONSE, TriageRequest, TriageResponse

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

app = FastAPI(title="PRism")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/triage", response_model=TriageResponse)
def triage(body: TriageRequest) -> TriageResponse:
    # pr = fetch_pr(body.pr_url)
    # signals = extract_signals(pr)
    # context = repo_context(pr.author, f"{pr.owner}/{pr.repo}")
    # return judge(pr, signals, context)
    return EXAMPLE_RESPONSE.model_copy(update={"pr_url": body.pr_url})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")
