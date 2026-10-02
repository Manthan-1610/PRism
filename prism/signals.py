"""Deterministic checks. Diveet owns this file.

Implement extract_signals(pr) -> list[Signal].
Each signal is a pure function of the PullRequest dict:
whitespace_only, size, has_tests, linked_issue, followed_contributing.
author_pr_velocity_7d is filled from Snowflake context, not here.
A missing CONTRIBUTING file is not a penalty.
"""

from prism.contract import PullRequest, Signal


def extract_signals(pr: PullRequest) -> list[Signal]:
    raise NotImplementedError("Diveet: implement signal extractors in prism/signals.py")
