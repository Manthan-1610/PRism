"""Snowflake history lookup. Diveet owns this file.

Implement repo_context(author, repo_full_name) -> SnowflakeContext.
Read queries/github_context.sql (written by CoCo) and bind author plus repo.
Filter to PullRequestEvent in the last 7 days.
On failure, or when SNOWFLAKE_DISABLED=1, load fixtures/ and set source to cache.
Never format user input into the SQL string. Use connector parameters.
"""

from prism.contract import SnowflakeContext


def repo_context(author: str, repo_full_name: str) -> SnowflakeContext:
    raise NotImplementedError("Diveet: implement Snowflake context in prism/context.py")
