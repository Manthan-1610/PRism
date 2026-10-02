# PRism

Triage a public GitHub pull request with deterministic checks, a Snowflake GitHub-events query, and an open-weight model cascade.

This tree is a stub. Each module raises `NotImplementedError` until that owner fills it in. `POST /triage` currently returns the example contract so the UI can be built in parallel.

## Open-weight models

Every verdict comes from an open-weight model. No proprietary model is called anywhere in the pipeline.

| Role | Model | Publisher | Parameters | Price per 1M tokens (input / output) |
| --- | --- | --- | --- | --- |
| Small judge, runs on every PR | `mistral-3-14B` (Ministral 3 14B Instruct) | Mistral AI | 14B | $0.20 / $0.20 |
| Escalation judge, runs only when needed | `llama-4-maverick` (Llama 4 Maverick 17B 128E Instruct) | Meta | about 400B total | $0.25 / $0.87 |

Both run on DigitalOcean serverless inference at `https://inference.do-ai.run/v1` through its OpenAI-compatible chat completions endpoint. Model ids and prices are set in `.env`, so any other open-weight model on that endpoint can be swapped in.

## How the judge works

`prism/judge.py` is an original harness around those two models:

1. **Measured facts first.** The model receives the PR title, body, a capped excerpt of the diff, the deterministic signals computed in `prism/signals.py`, and the author's recent public pull-request activity from Snowflake. The system prompt in `skill/prism-triage/references/rubric.md` tells it to trust those measurements over its own reading of the diff.
2. **Strict JSON with repair.** The model must return a verdict (`ship_it`, `needs_work`, or `likely_spam`), a confidence, evidence lines, a reply to the contributor, and a summary for the maintainer. Output is validated against a Pydantic schema. Invalid output is sent back with the validation error, up to two repairs.
3. **Cascade.** The small model answers first. The large model runs only when the small model is unsure or contradicts the measurements:
   - confidence below 0.6
   - verdict `ship_it` on a whitespace-only diff
   - verdict `ship_it` from an author with 10 or more PR events in 7 days on a diff of 5 lines or fewer

   An escalation can only make a verdict stricter. If the large model would move an unsure verdict toward `ship_it`, PRism keeps the stricter verdict and notes the disagreement in the maintainer summary, so no PR is waved through on a second opinion alone. Each model call times out after 45 seconds, and a failed escalation falls back to the small model's verdict.
4. **Cost and provenance.** Every response records which model produced the verdict, whether it escalated, and the dollar cost computed from token usage.

The contributor reply is written to be kind and specific. It names the file or missing piece, says what a mergeable version would contain, and never calls the author a spammer.

## Evaluation

`eval/labeled.csv` holds 15 real public pull requests from Hacktoberfest-era repositories: 5 `likely_spam`, 5 `needs_work`, and 5 `ship_it`. Labels follow the maintainers' own outcome where one exists: a `spam` or `invalid` label, a changes-requested review, or a merge. Each row has a note explaining the label.

```powershell
.\.venv\Scripts\python.exe eval\run_eval.py
```

The script scores small-only against the cascade and prints accuracy, mean cost per PR, and how many PRs escalated.

| Mode | Accuracy | Mean cost per PR | Escalated |
| --- | --- | --- | --- |
| Small model only | 13/15 | $0.0004 | 0 |
| Cascade | 13/15 | $0.0005 | 3 |

On this set the cascade matches the small model's accuracy rather than beating it. Its value is caution: on 3 of 15 PRs the small model was unsure and a second open model was consulted, and in one of those the large model would have upgraded a flawed PR to `ship_it` and was overruled. Both misses are hard cases: a PR whose body claims a reformat while the diff only adds a comment, and a well-explained single-file solution with no tests.

An earlier version let the large model's verdict win outright. It scored 11/15, because Llama 4 Maverick tended to trust a PR's own description. That result is why escalation can now only make verdicts stricter. Qwen 3.5 397B was also tried as the escalation model and timed out on this endpoint.

## Who owns what

| Path | Owner | Job |
| --- | --- | --- |
| `prism/contract.py` | Shared | JSON shape. Change it together. |
| `prism/ingest.py` | Diveet | GitHub fetch |
| `prism/signals.py` | Diveet | Deterministic checks |
| `prism/context.py` | Diveet | Snowflake query |
| `queries/github_context.sql` | Diveet | SQL from CoCo |
| `prism/judge.py` | Manthan | Prompts, cascade, cost |
| `skill/prism-triage/references/rubric.md` | Manthan | System prompt |
| `eval/run_eval.py` | Manthan | Accuracy and cost |
| `prism/api.py` | Rohith | FastAPI wiring |
| `skill/prism-triage/` | Rohith | Agent skill |
| `web/` | Chahat | Verdict screen |
| `eval/labeled.csv` | Chahat | 15 labeled PR URLs |

## Run the stub

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python.exe -m uvicorn prism.api:app --reload --port 8000
```

Open `http://127.0.0.1:8000`.

## Pipeline to wire in `prism/api.py`

```python
pr = fetch_pr(body.pr_url)
signals = extract_signals(pr)
context = repo_context(pr.author, f"{pr.owner}/{pr.repo}")
return judge(pr, signals, context)
```
