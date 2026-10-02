---
name: prism-triage
description: Triage a public GitHub pull request for Hacktoberfest maintainer review into ship_it, needs_work, or likely_spam. Combines deterministic diff signals, Snowflake public PullRequestEvent history, and an open-weight judge that returns evidence plus a kind contributor reply. Use when the user pastes a github.com pull request URL, or asks whether a PR is spam, self-promotion, ready to merge, needs work, or is a drive-by contribution.
license: MIT
---

# PRism triage

Use this skill to classify one public GitHub PR the way a cautious open-source maintainer would during Hacktoberfest.

## When to use

- User pastes a `https://github.com/.../pull/...` URL
- User asks if a PR is spam, self-promotion, mergeable, or needs changes
- User wants a kind reply to leave on a Hacktoberfest contribution

## Run

From the repository root:

```bash
python skill/prism-triage/scripts/triage.py https://github.com/owner/repo/pull/123
```

## Before changing verdicts

Read `references/rubric.md`. It is the system prompt for the open-weight judge and defines:

- `ship_it` / `needs_work` / `likely_spam` for Hacktoberfest spam patterns (whitespace-only, README self-promotion, drive-by docs, high author velocity on tiny diffs)
- how to treat truncated patches and Snowflake counts
- tone rules so contributor replies stay specific and never accusatory

## Show the user

1. `verdict` and `confidence`
2. every item in `evidence`
3. `contributor_reply`

Keep `maintainer_summary` for the maintainer. Mention Snowflake source when present (`snowflake`, `cache`, or `unavailable`).
