"""Shared response shape. Agree on this file before changing field names."""

from typing import Literal

from pydantic import BaseModel, Field

Verdict = Literal["ship_it", "needs_work", "likely_spam"]
ContextSource = Literal["snowflake", "cache", "unavailable"]


class TriageRequest(BaseModel):
    pr_url: str


class PrFile(BaseModel):
    filename: str
    patch: str = ""
    additions: int = 0
    deletions: int = 0


class PullRequest(BaseModel):
    url: str
    owner: str
    repo: str
    number: int
    title: str
    body: str = ""
    author: str
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    files: list[PrFile] = Field(default_factory=list)


class Signal(BaseModel):
    signal: str
    detail: str
    value: bool | int | float | None = None


class Evidence(BaseModel):
    signal: str
    detail: str


class Signals(BaseModel):
    lines_changed: int
    has_tests: bool
    linked_issue: bool
    followed_contributing: bool
    author_pr_velocity_7d: int | None = None


class SnowflakeContext(BaseModel):
    dataset: str
    author_pr_events_7d: int | None = None
    repo_pr_events_7d: int | None = None
    source: ContextSource = "unavailable"


class TriageResponse(BaseModel):
    pr_url: str
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence]
    signals: Signals
    snowflake_context: SnowflakeContext
    contributor_reply: str
    maintainer_summary: str
    model_used: str
    escalated: bool
    cost_usd: float


EXAMPLE_RESPONSE = TriageResponse(
    pr_url="https://github.com/owner/repo/pull/1",
    verdict="needs_work",
    confidence=0.72,
    evidence=[
        Evidence(signal="has_tests", detail="no test file among 3 changed files"),
    ],
    signals=Signals(
        lines_changed=40,
        has_tests=False,
        linked_issue=False,
        followed_contributing=False,
        author_pr_velocity_7d=14,
    ),
    snowflake_context=SnowflakeContext(
        dataset="replace-with-listing-name",
        author_pr_events_7d=14,
        repo_pr_events_7d=6,
        source="cache",
    ),
    contributor_reply="Thanks for opening this. Add a test covering the changed path and link the issue it fixes.",
    maintainer_summary="Real attempt, no tests, no linked issue.",
    model_used="small-model-id",
    escalated=False,
    cost_usd=0.0004,
)
