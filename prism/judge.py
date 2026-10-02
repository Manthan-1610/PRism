"""Open-weight judge and cascade. Manthan owns this file.

Implement judge(pr, signals, context) -> TriageResponse.
Call SMALL_MODEL at https://inference.do-ai.run/v1 with temperature 0.
Prompt text lives in skill/prism-triage/references/rubric.md.
Strip ```json fences, validate with TriageResponse, retry at most twice.
Escalate to LARGE_MODEL when confidence < 0.6, or when ship_it conflicts
with whitespace_only, or when ship_it coincides with high author velocity
and a tiny diff. Record token cost from the rates in .env.
"""

from prism.contract import PullRequest, Signal, SnowflakeContext, TriageResponse


def judge(
    pr: PullRequest,
    signals: list[Signal],
    context: SnowflakeContext,
) -> TriageResponse:
    raise NotImplementedError("Manthan: implement the judge in prism/judge.py")
