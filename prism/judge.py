"""Open-weight judge and cascade."""

import json
import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field, ValidationError

from prism.contract import (
    Evidence,
    PullRequest,
    Signal,
    Signals,
    SnowflakeContext,
    TriageResponse,
    Verdict,
)

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
RUBRIC_PATH = ROOT / "skill" / "prism-triage" / "references" / "rubric.md"
BASE_URL = "https://inference.do-ai.run/v1"

MAX_REPAIRS = 2
ESCALATE_BELOW = 0.6
HIGH_VELOCITY = 10
TINY_DIFF = 5
BODY_LIMIT = 2000
FILE_LIMIT = 20
PATCH_LIMIT = 500
PAYLOAD_LIMIT = 8000


class ModelVerdict(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence]
    contributor_reply: str
    maintainer_summary: str


class ModelResult(BaseModel):
    model: str
    verdict: ModelVerdict
    cost_usd: float


@lru_cache(maxsize=1)
def client() -> OpenAI:
    return OpenAI(base_url=BASE_URL, api_key=os.environ["MODEL_ACCESS_KEY"])


@lru_cache(maxsize=1)
def load_rubric() -> str:
    return RUBRIC_PATH.read_text(encoding="utf-8")


def _rates(tier: str) -> tuple[float, float]:
    return (
        float(os.environ.get(f"{tier}_INPUT_PER_MILLION", "0")),
        float(os.environ.get(f"{tier}_OUTPUT_PER_MILLION", "0")),
    )


def build_user_payload(
    pr: PullRequest,
    signals: list[Signal],
    context: SnowflakeContext,
) -> str:
    payload = {
        "title": pr.title,
        "body": pr.body[:BODY_LIMIT],
        "author": pr.author,
        "repo": f"{pr.owner}/{pr.repo}",
        "additions": pr.additions,
        "deletions": pr.deletions,
        "changed_files": pr.changed_files,
        "signals": [s.model_dump() for s in signals],
        "snowflake_context": {
            "author_pr_events_7d": context.author_pr_events_7d,
            "repo_pr_events_7d": context.repo_pr_events_7d,
        },
        "files": [],
    }
    size = len(json.dumps(payload))
    for f in pr.files[:FILE_LIMIT]:
        entry = {"filename": f.filename, "patch": f.patch[:PATCH_LIMIT]}
        entry_size = len(json.dumps(entry))
        if size + entry_size > PAYLOAD_LIMIT:
            entry = {"filename": f.filename}
            entry_size = len(json.dumps(entry))
            if size + entry_size > PAYLOAD_LIMIT:
                break
        payload["files"].append(entry)
        size += entry_size
    return json.dumps(payload)


def parse_json(text: str) -> dict:
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


def _ask(model: str, tier: str, payload: str) -> ModelResult:
    input_rate, output_rate = _rates(tier)
    messages = [
        {"role": "system", "content": load_rubric()},
        {"role": "user", "content": payload},
    ]
    cost = 0.0
    last_error = ""
    for _ in range(MAX_REPAIRS + 1):
        try:
            resp = client().chat.completions.create(
                model=model,
                temperature=0,
                max_completion_tokens=800,
                messages=messages,
            )
        except OpenAIError as exc:
            raise RuntimeError(f"{model} call failed: {exc}") from exc
        if resp.usage:
            cost += resp.usage.prompt_tokens / 1_000_000 * input_rate
            cost += resp.usage.completion_tokens / 1_000_000 * output_rate
        text = resp.choices[0].message.content or ""
        try:
            verdict = ModelVerdict.model_validate(parse_json(text))
            return ModelResult(model=model, verdict=verdict, cost_usd=cost)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)
            messages += [
                {"role": "assistant", "content": text},
                {"role": "user", "content": f"Validation failed: {last_error}. Return only corrected JSON."},
            ]
    raise RuntimeError(f"{model} returned invalid JSON after {MAX_REPAIRS} repairs: {last_error}")


def _signal_value(signals: list[Signal], name: str):
    for s in signals:
        if s.signal == name:
            return s.value
    return None


def build_signals(pr: PullRequest, signals: list[Signal], context: SnowflakeContext) -> Signals:
    size = _signal_value(signals, "size")
    return Signals(
        lines_changed=int(size) if isinstance(size, (int, float)) else pr.additions + pr.deletions,
        has_tests=bool(_signal_value(signals, "has_tests")),
        linked_issue=bool(_signal_value(signals, "linked_issue")),
        followed_contributing=bool(_signal_value(signals, "followed_contributing")),
        author_pr_velocity_7d=context.author_pr_events_7d,
    )


def should_escalate(result: ModelVerdict, pr: PullRequest, signals: list[Signal], context: SnowflakeContext) -> bool:
    if result.confidence < ESCALATE_BELOW:
        return True
    if result.verdict != "ship_it":
        return False
    if _signal_value(signals, "whitespace_only") is True:
        return True
    velocity = context.author_pr_events_7d or 0
    return velocity >= HIGH_VELOCITY and pr.additions + pr.deletions <= TINY_DIFF


def _response(
    pr: PullRequest,
    signals: Signals,
    context: SnowflakeContext,
    result: ModelResult,
    escalated: bool,
    cost_usd: float,
    summary_note: str = "",
) -> TriageResponse:
    v = result.verdict
    summary = f"{v.maintainer_summary} {summary_note}".strip()
    return TriageResponse(
        pr_url=pr.url,
        verdict=v.verdict,
        confidence=v.confidence,
        evidence=v.evidence,
        signals=signals,
        snowflake_context=context,
        contributor_reply=v.contributor_reply,
        maintainer_summary=summary,
        model_used=result.model,
        escalated=escalated,
        cost_usd=round(cost_usd, 6),
    )


def judge(
    pr: PullRequest,
    signals: list[Signal],
    context: SnowflakeContext,
    escalate: bool = True,
) -> TriageResponse:
    payload = build_user_payload(pr, signals, context)
    response_signals = build_signals(pr, signals, context)
    small = _ask(os.environ["SMALL_MODEL"], "SMALL", payload)

    if not escalate or not should_escalate(small.verdict, pr, signals, context):
        return _response(pr, response_signals, context, small, False, small.cost_usd)

    try:
        large = _ask(os.environ["LARGE_MODEL"], "LARGE", payload)
    except RuntimeError as exc:
        return _response(
            pr, response_signals, context, small, True, small.cost_usd,
            summary_note=f"(Escalation failed: {exc})",
        )
    return _response(pr, response_signals, context, large, True, small.cost_usd + large.cost_usd)


def _fake_cases() -> list[tuple[str, PullRequest, list[Signal], SnowflakeContext]]:
    spam = PullRequest(
        url="https://github.com/example/docs/pull/101",
        owner="example",
        repo="docs",
        number=101,
        title="add my name to README",
        body="",
        author="octocat",
        additions=1,
        deletions=1,
        changed_files=1,
        files=[{"filename": "README.md", "patch": "@@ -3 +3 @@\n-Contributors\n+Contributors \n"}],
    )
    spam_signals = [
        Signal(signal="whitespace_only", detail="1 of 1 changed lines is whitespace", value=True),
        Signal(signal="size", detail="2 lines across 1 file", value=2),
        Signal(signal="has_tests", detail="no test files changed", value=False),
        Signal(signal="linked_issue", detail="body references no issue", value=False),
        Signal(signal="followed_contributing", detail="CONTRIBUTING.md exists, body is empty", value=False),
    ]
    spam_ctx = SnowflakeContext(dataset="fixture", author_pr_events_7d=14, repo_pr_events_7d=2, source="cache")

    real = PullRequest(
        url="https://github.com/example/app/pull/12",
        owner="example",
        repo="app",
        number=12,
        title="Handle empty config file without crashing",
        body="Fixes #12. load_config now returns defaults when the file is empty. Added a regression test.",
        author="newcontributor",
        additions=24,
        deletions=3,
        changed_files=2,
        files=[
            {"filename": "app/config.py", "patch": "+    if not text.strip():\n+        return DEFAULTS\n"},
            {"filename": "tests/test_app.py", "patch": "+def test_empty_config_returns_defaults(tmp_path):\n+    ...\n"},
        ],
    )
    real_signals = [
        Signal(signal="whitespace_only", detail="0 of 27 changed lines are whitespace", value=False),
        Signal(signal="size", detail="27 lines across 2 files", value=27),
        Signal(signal="has_tests", detail="tests/test_app.py changed", value=True),
        Signal(signal="linked_issue", detail="body says Fixes #12", value=True),
        Signal(signal="followed_contributing", detail="no CONTRIBUTING file in repo", value=True),
    ]
    real_ctx = SnowflakeContext(dataset="fixture", author_pr_events_7d=1, repo_pr_events_7d=6, source="cache")
    return [("spam", spam, spam_signals, spam_ctx), ("real", real, real_signals, real_ctx)]


if __name__ == "__main__":
    for name, pr, sigs, ctx in _fake_cases():
        result = judge(pr, sigs, ctx)
        print(f"--- {name}")
        print(result.model_dump_json(indent=2))
