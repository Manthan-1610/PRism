-- Public GitHub history from Snowflake Public Data (Free).
-- View: SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GITHUB_EVENTS
-- Columns checked in the account: TYPE, ACTOR_LOGIN, REPO_NAME, CREATED_AT_TIMESTAMP.
-- Filter on CREATED_AT_TIMESTAMP. Do not filter the CREATED_AT string column.
-- Bind names: author (GitHub login), repo (owner/repo). Do not string-format this file.
-- The free listing lags about three months, so the 7-day window ends at the newest
-- matching PullRequestEvent instead of the current time.

WITH params AS (
    SELECT
        %(author)s AS author_login,
        %(repo)s AS repo_name
),
recent AS (
    SELECT
        events.ACTOR_LOGIN,
        events.REPO_NAME,
        events.CREATED_AT_TIMESTAMP AS ts
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GITHUB_EVENTS AS events
    CROSS JOIN params
    WHERE events.TYPE = 'PullRequestEvent'
      AND events.CREATED_AT_TIMESTAMP >= DATEADD(day, -180, CURRENT_TIMESTAMP())
      AND (
          events.ACTOR_LOGIN = params.author_login
          OR events.REPO_NAME = params.repo_name
      )
),
windowed AS (
    SELECT
        recent.ACTOR_LOGIN = params.author_login AS is_author,
        recent.REPO_NAME = params.repo_name AS is_repo,
        recent.ts,
        DATEADD(day, -7, MAX(recent.ts) OVER ()) AS since_ts
    FROM recent
    CROSS JOIN params
)
SELECT
    COUNT_IF(is_author AND ts >= since_ts) AS author_pr_events_7d,
    COUNT_IF(is_repo AND ts >= since_ts) AS repo_pr_events_7d
FROM windowed
