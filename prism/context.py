"""Snowflake history lookup. Diveet owns this file.

repo_context(author, repo_full_name) -> SnowflakeContext.
The SQL file is parameterized. Author and repo are never interpolated.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from prism.contract import SnowflakeContext

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

SQL_PATH = ROOT / "queries" / "github_context.sql"
FIXTURES = ROOT / "fixtures"
DATASET = "Snowflake Public Data (Free)"
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")
logger = logging.getLogger("prism.context")


def repo_context(author: str, repo_full_name: str) -> SnowflakeContext:
    author = author.strip()
    repo_full_name = repo_full_name.strip()
    if os.environ.get("SNOWFLAKE_DISABLED", "0").strip() == "1":
        cached = _from_cache(author, repo_full_name)
        logger.info(
            "Snowflake disabled; using %s for %s in %s",
            cached.source,
            author,
            repo_full_name,
        )
        return cached

    try:
        found = _query_snowflake(author, repo_full_name)
    except Exception as exc:
        # Never log credential values; the exception type/message is enough.
        logger.warning(
            "Snowflake query failed for %s in %s (%s: %s); falling back to cache",
            author,
            repo_full_name,
            type(exc).__name__,
            exc,
        )
        return _from_cache(author, repo_full_name)

    _write_cache(author, repo_full_name, found)
    logger.info(
        "Snowflake live for %s in %s: author=%s repo=%s",
        author,
        repo_full_name,
        found.author_pr_events_7d,
        found.repo_pr_events_7d,
    )
    return found


def _query_snowflake(author: str, repo_full_name: str) -> SnowflakeContext:
    import snowflake.connector
    from snowflake.connector import DictCursor

    sql = SQL_PATH.read_text(encoding="utf-8")
    account = _required("SNOWFLAKE_ACCOUNT")
    conn = snowflake.connector.connect(
        account=account,
        user=_required("SNOWFLAKE_USER"),
        password=_required("SNOWFLAKE_PASSWORD"),
        warehouse=_required("SNOWFLAKE_WAREHOUSE"),
        database=_required("SNOWFLAKE_DATABASE"),
        schema=_required("SNOWFLAKE_SCHEMA"),
        role=_required("SNOWFLAKE_ROLE"),
        login_timeout=20,
        network_timeout=30,
    )
    try:
        with conn.cursor(DictCursor) as cur:
            cur.execute("ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = 30")
            cur.execute(sql, {"author": author, "repo": repo_full_name})
            row = cur.fetchone() or {}
    finally:
        conn.close()

    return SnowflakeContext(
        dataset=DATASET,
        author_pr_events_7d=_count(row, "author_pr_events_7d"),
        repo_pr_events_7d=_count(row, "repo_pr_events_7d"),
        source="snowflake",
    )


def _from_cache(author: str, repo_full_name: str) -> SnowflakeContext:
    path = _cache_path(author, repo_full_name)
    if not path.exists():
        return SnowflakeContext(dataset=DATASET, source="unavailable")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SnowflakeContext(
        dataset=str(payload.get("dataset") or DATASET),
        author_pr_events_7d=_optional_int(payload.get("author_pr_events_7d")),
        repo_pr_events_7d=_optional_int(payload.get("repo_pr_events_7d")),
        source="cache",
    )


def _write_cache(author: str, repo_full_name: str, context: SnowflakeContext) -> None:
    path = _cache_path(author, repo_full_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "dataset": context.dataset,
                "author_pr_events_7d": context.author_pr_events_7d,
                "repo_pr_events_7d": context.repo_pr_events_7d,
            }
        ),
        encoding="utf-8",
    )


def _cache_path(author: str, repo_full_name: str) -> Path:
    return FIXTURES / f"context_{_safe(author)}__{_safe(repo_full_name)}.json"


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def _count(row: dict, name: str) -> int:
    for key in (name, name.upper(), name.lower()):
        if key in row and row[key] is not None:
            return int(row[key])
    return 0


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _safe(value: str) -> str:
    return _SAFE.sub("_", value).strip("._") or "unknown"
