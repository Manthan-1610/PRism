"""GitHub fetch. Diveet owns this file.

fetch_pr(url) -> PullRequest for https://github.com/{owner}/{repo}/pull/{number}.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

from prism.contract import PrFile, PullRequest

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
GITHUB_API = "https://api.github.com"
PATCH_CAP = 2000
FILE_CAP = 20
CONTRIBUTING_PATHS = (
    "CONTRIBUTING.md",
    "CONTRIBUTING",
    ".github/CONTRIBUTING.md",
)

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


class IngestError(RuntimeError):
    """A pull request URL could not be fetched."""


def fetch_pr(url: str) -> PullRequest:
    owner, repo, number = parse_pr_url(url)
    path = fixture_path(owner, repo, number)
    if _use_cache() and path.exists():
        return _pr_from_fixture(path, url)

    pr_payload = _github_json(f"/repos/{owner}/{repo}/pulls/{number}")
    files_payload = _github_json(
        f"/repos/{owner}/{repo}/pulls/{number}/files",
        params={"per_page": FILE_CAP},
    )
    if not isinstance(files_payload, list):
        raise IngestError("GitHub files response was not a list")
    has_contributing = repo_has_contributing(owner, repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "pr": pr_payload,
                "files": files_payload,
                "has_contributing": has_contributing,
            }
        ),
        encoding="utf-8",
    )
    return _normalize(url, owner, repo, number, pr_payload, files_payload)


def repo_has_contributing(owner: str, repo: str) -> bool | None:
    """True when a CONTRIBUTING file exists, False when all three paths 404.

    None means GitHub could not be checked. Callers must not treat that as a penalty.
    """
    for rel in CONTRIBUTING_PATHS:
        status = _github_status(f"/repos/{owner}/{repo}/contents/{rel}")
        if status == 200:
            return True
        if status == 404:
            continue
        return None
    return False


def cached_contributing(owner: str, repo: str, number: int) -> bool | None:
    path = fixture_path(owner, repo, number)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get("has_contributing")
    if isinstance(value, bool):
        return value
    return None


def parse_pr_url(url: str) -> tuple[str, str, int]:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if parsed.scheme not in {"http", "https"} or host != "github.com":
        raise IngestError("URL must be a public GitHub pull request")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 4 or parts[2] != "pull" or not parts[3].isdigit():
        raise IngestError(
            "URL must look like https://github.com/{owner}/{repo}/pull/{number}"
        )
    return parts[0], parts[1], int(parts[3])


def fixture_path(owner: str, repo: str, number: int) -> Path:
    return FIXTURES / f"{_safe(owner)}__{_safe(repo)}__{number}.json"


def _normalize(
    url: str,
    owner: str,
    repo: str,
    number: int,
    pr_payload: dict,
    files_payload: list,
) -> PullRequest:
    user = pr_payload.get("user") or {}
    files: list[PrFile] = []
    for item in files_payload[:FILE_CAP]:
        files.append(
            PrFile(
                filename=str(item.get("filename") or ""),
                patch=str(item.get("patch") or "")[:PATCH_CAP],
                additions=int(item.get("additions") or 0),
                deletions=int(item.get("deletions") or 0),
            )
        )
    return PullRequest(
        url=url,
        owner=owner,
        repo=repo,
        number=number,
        title=str(pr_payload.get("title") or ""),
        body=str(pr_payload.get("body") or ""),
        author=str(user.get("login") or ""),
        additions=int(pr_payload.get("additions") or 0),
        deletions=int(pr_payload.get("deletions") or 0),
        changed_files=int(pr_payload.get("changed_files") or len(files)),
        files=files,
    )


def _pr_from_fixture(path: Path, url: str) -> PullRequest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    owner, repo, number = parse_pr_url(url)
    return _normalize(url, owner, repo, number, payload["pr"], payload["files"])


def _github_json(path: str, params: dict | None = None) -> dict | list:
    response = _github_request(path, params)
    if response.status_code == 404:
        raise IngestError("public PR not found")
    _raise_for_rate_limit(response)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise IngestError(f"GitHub request failed ({response.status_code})") from exc
    return response.json()


def _github_status(path: str) -> int:
    response = _github_request(path)
    if response.status_code in {403, 429}:
        return response.status_code
    return response.status_code


def _github_request(path: str, params: dict | None = None) -> httpx.Response:
    try:
        with httpx.Client(timeout=20.0) as client:
            return client.get(f"{GITHUB_API}{path}", headers=_headers(), params=params)
    except httpx.HTTPError as exc:
        raise IngestError(f"GitHub request failed: {exc}") from exc


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "prism-triage",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _raise_for_rate_limit(response: httpx.Response) -> None:
    if response.status_code not in {403, 429}:
        return
    remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
    raise IngestError(
        "GitHub token is missing or the rate limit is hit "
        f"(X-RateLimit-Remaining={remaining})"
    )


def _use_cache() -> bool:
    return os.environ.get("PRISM_USE_CACHE", "0").strip() == "1"


def _safe(value: str) -> str:
    return _SAFE.sub("_", value).strip("._") or "unknown"
