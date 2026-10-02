-- Public GitHub history from the Snowflake Public Data (Paid) trial.
-- View: SNOWFLAKE_PUBLIC_DATA_PAID.PUBLIC_DATA.GITHUB_EVENTS
-- Columns checked in the account: TYPE, ACTOR_LOGIN, REPO_NAME, CREATED_AT_TIMESTAMP.
-- Filter on CREATED_AT_TIMESTAMP. Do not filter the CREATED_AT string column.
-- Bind names: author (GitHub login), repo (owner/repo). Do not string-format this file.

WITH params AS (
    SELECT
        %(author)s AS author_login,
        %(repo)s AS repo_name,
        DATEADD(day, -7, CURRENT_TIMESTAMP()) AS since_ts
)
SELECT
    COUNT_IF(events.ACTOR_LOGIN = params.author_login) AS author_pr_events_7d,
    COUNT_IF(events.REPO_NAME = params.repo_name) AS repo_pr_events_7d
FROM SNOWFLAKE_PUBLIC_DATA_PAID.PUBLIC_DATA.GITHUB_EVENTS AS events
CROSS JOIN params
WHERE events.TYPE = 'PullRequestEvent'
  AND events.CREATED_AT_TIMESTAMP >= params.since_ts
  AND (
      events.ACTOR_LOGIN = params.author_login
      OR events.REPO_NAME = params.repo_name
  )
