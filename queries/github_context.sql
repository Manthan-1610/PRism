-- Diveet: replace this file with the SELECT CoCo generates.
-- Bind parameters for the actor login and the repo full name (owner/repo).
-- Required output columns: author_pr_events_7d, repo_pr_events_7d
-- Required filters: PullRequestEvent only, last 7 days only.
-- Use the column names from the dataset CoCo described. Do not scan the full archive.

SELECT
    CAST(NULL AS INTEGER) AS author_pr_events_7d,
    CAST(NULL AS INTEGER) AS repo_pr_events_7d
WHERE FALSE;
