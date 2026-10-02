---
name: prism-triage
description: Triage a public GitHub pull request into ship_it, needs_work, or likely_spam using deterministic checks, Snowflake GitHub-event history, and an open-weight model. Use when the user pastes a github.com pull request URL or asks whether a PR is spam, ready to merge, or needs work.
license: MIT
---

# PRism triage

Run this from the repository root:

```bash
python skill/prism-triage/scripts/triage.py https://github.com/owner/repo/pull/123
```

`references/rubric.md` is the scoring rubric the judge uses to produce a verdict — read it if you need to explain why a verdict came out the way it did.

Show the user three things from the JSON result:

1. `verdict` and `confidence`
2. every item in `evidence`
3. `contributor_reply`

Keep `maintainer_summary` for the maintainer. The reply to the contributor must stay specific and must not call the author a spammer.
