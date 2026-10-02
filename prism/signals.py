"""Deterministic checks. Diveet owns this file.

extract_signals(pr) -> list[Signal]. No model calls.
author_pr_velocity_7d comes from Snowflake context, not from here.
"""

from __future__ import annotations

import re

from prism.contract import PullRequest, Signal
from prism.ingest import cached_contributing, repo_has_contributing

_ISSUE = re.compile(
    r"(?i)(?:\b(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?)\s+#\d+)|(?:#\d+)"
)
_TEST_MARKERS = ("/test", "test_", "_test.", ".spec.", "/tests/")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _author_text(body: str | None) -> str:
    """PR body without template comments, which are not written by the author."""
    return _HTML_COMMENT.sub("", body or "").strip()


def extract_signals(pr: PullRequest) -> list[Signal]:
    has_file = cached_contributing(pr.owner, pr.repo, pr.number)
    if has_file is None:
        has_file = repo_has_contributing(pr.owner, pr.repo)
    return [
        _whitespace_only(pr),
        _size(pr),
        _has_tests(pr),
        _linked_issue(pr),
        _followed_contributing(pr, has_file),
    ]


def _whitespace_only(pr: PullRequest) -> Signal:
    changed = _changed_lines(pr)
    if not changed:
        return Signal(
            signal="whitespace_only",
            detail="no text diff to inspect",
            value=False,
        )
    blank = sum(1 for line in changed if line.strip() == "")
    return Signal(
        signal="whitespace_only",
        detail=f"{blank} of {len(changed)} changed lines are whitespace",
        value=blank == len(changed),
    )


def _size(pr: PullRequest) -> Signal:
    lines = pr.additions + pr.deletions
    return Signal(
        signal="size",
        detail=f"{lines} lines across {pr.changed_files} files",
        value=lines,
    )


def _has_tests(pr: PullRequest) -> Signal:
    tested = [item.filename for item in pr.files if _is_test_path(item.filename)]
    checked = len(pr.files)
    if tested:
        detail = f"test file present: {tested[0]}"
    elif pr.changed_files > checked:
        detail = f"no test file among the first {checked} of {pr.changed_files} files"
    else:
        detail = f"no test file among {checked} changed files"
    return Signal(signal="has_tests", detail=detail, value=bool(tested))


def _linked_issue(pr: PullRequest) -> Signal:
    matched = _ISSUE.search(f"{pr.title}\n{_author_text(pr.body)}")
    if matched:
        return Signal(
            signal="linked_issue",
            detail=f"title or body links an issue ({matched.group(0)})",
            value=True,
        )
    return Signal(
        signal="linked_issue",
        detail="title and body do not link an issue",
        value=False,
    )


def _followed_contributing(pr: PullRequest, has_file: bool | None) -> Signal:
    if has_file is not True:
        if has_file is False:
            detail = "repo has no CONTRIBUTING file, so this check does not penalize the author"
        else:
            detail = "CONTRIBUTING check unavailable, so this check does not penalize the author"
        return Signal(signal="followed_contributing", detail=detail, value=True)
    text = _author_text(pr.body)
    followed = "- [x]" in text.lower() or len(text) > 200
    if followed:
        detail = "body is long enough or checks a CONTRIBUTING box"
    else:
        detail = "repo has CONTRIBUTING and the body does not follow it"
    return Signal(signal="followed_contributing", detail=detail, value=followed)


def _changed_lines(pr: PullRequest) -> list[str]:
    changed: list[str] = []
    for item in pr.files:
        for line in (item.patch or "").splitlines():
            if line.startswith("+++") or line.startswith("---") or line.startswith("\\"):
                continue
            if line.startswith("+") or line.startswith("-"):
                changed.append(line[1:])
    return changed


def _is_test_path(filename: str) -> bool:
    lowered = filename.lower()
    if any(marker in lowered for marker in _TEST_MARKERS):
        return True
    parts = lowered.split("/")
    if any(part in {"test", "tests"} for part in parts[:-1]):
        return True
    base = parts[-1]
    return base.startswith("test_") or base.endswith("_test.py") or base.endswith("_test.ts")
