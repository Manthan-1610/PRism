"""GitHub fetch. Diveet owns this file.

Implement fetch_pr(url) -> PullRequest.
Parse https://github.com/{owner}/{repo}/pull/{number}.
GET /repos/{owner}/{repo}/pulls/{number}
GET /repos/{owner}/{repo}/pulls/{number}/files?per_page=20
Headers: Authorization Bearer GITHUB_TOKEN, Accept application/vnd.github+json,
X-GitHub-Api-Version 2022-11-28.
Cap each patch at 2000 characters. Cache raw JSON under fixtures/.
When PRISM_USE_CACHE=1, return the fixture and skip the network.
404 means the PR is missing or private. 403/429 means token or rate limit.
"""

from prism.contract import PullRequest


def fetch_pr(url: str) -> PullRequest:
    raise NotImplementedError("Diveet: implement GitHub fetch in prism/ingest.py")
