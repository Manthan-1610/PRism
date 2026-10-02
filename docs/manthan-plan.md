# Manthan: judge, cascade, and eval

Manthan owns the judging brain. He picks two open-weight models on DigitalOcean, turns a pull request plus Diveet’s signals into valid JSON, escalates to the larger model only when the small one is unsure, and leaves the expo with a measured accuracy and cost.

He does not fetch GitHub, write SQL, or build the page. Deadline is 3:30 PM. Feature freeze is 2:45 PM.

## Files he owns

| File | What he does with it |
| --- | --- |
| `prism/judge.py` | Model call, JSON repair, cascade, cost, copy-through of signals and Snowflake context |
| `skill/prism-triage/references/rubric.md` | System prompt, loaded at runtime |
| `eval/run_eval.py` | Accuracy and mean cost for small-only vs cascade |

`prism/contract.py` is shared. Do not rename fields. `prism/api.py`, the skill script, and the UI belong to Rohith and Chahat. They call `judge` and use the object it returns.

## Locked decisions

**Signals and Snowflake context.** `judge` copies the real `signals` and `snowflake_context` from its arguments onto the `TriageResponse`. `api.py` returns that object unchanged. The skill script and `eval/run_eval.py` also call `judge` directly, so a later overwrite in `api.py` would leave them showing dummy numbers.

The model is asked only for `verdict`, `confidence`, `evidence`, `contributor_reply`, and `maintainer_summary`. Python fills `signals`, `snowflake_context`, `pr_url`, `model_used`, `escalated`, and `cost_usd`.

**Failure.** If `SMALL_MODEL` still returns invalid JSON after two repair attempts, or the API call itself fails, raise `RuntimeError` with the last error. Do not invent a verdict. Rohith maps that exception to an HTTP error body `{"error": "..."}`. The page already displays `error`.

If escalation runs and `LARGE_MODEL` fails the same way, return the small model’s object with `escalated=True` and append the large-model error to `maintainer_summary`. That is the last real verdict.

## Resources he uses

**DigitalOcean, $25 Hacktoberfest credit.** Activate at check-in. The inference host is `https://inference.do-ai.run/v1`. It is separate from `https://api.digitalocean.com`. Auth is `MODEL_ACCESS_KEY` in `.env`. The `openai` package is already in `requirements.txt`. Point it at DigitalOcean with `base_url`.

Use open-weight ids from `GET /v1/models` that morning (Llama, Qwen, Mistral, Gemma, or another clearly open-weight id). Leave any id containing `openai`, `anthropic`, or `arcee` unused. The credit does not cover those proprietary serverless models, and the open-source track requires an open-weight judge.

Copy that model page’s input and output prices into:

- `SMALL_INPUT_PER_MILLION`, `SMALL_OUTPUT_PER_MILLION`
- `LARGE_INPUT_PER_MILLION`, `LARGE_OUTPUT_PER_MILLION`

**Rubric file.** `skill/prism-triage/references/rubric.md` is the system prompt. Edit that file. Do not keep a second copy of the rules inside `judge.py`.

**Labels.** `eval/labeled.csv` columns are `pr_url,human_verdict,notes`. Chahat fills the rows. Verdicts are only `ship_it`, `needs_work`, and `likely_spam`.

**What he waits on.** `fetch_pr`, `extract_signals`, and `repo_context` are Diveet’s. Until they exist, test `judge` with a hand-built `PullRequest`, `list[Signal]`, and `SnowflakeContext` in a `main` block. Snowflake, CoCo, and the GitHub token are not his to set up.

Signal names Diveet will emit, and the cascade must look for:

- `whitespace_only` (bool)
- `size` (int, additions plus deletions)
- `has_tests` (bool)
- `linked_issue` (bool)
- `followed_contributing` (bool)

`author_pr_velocity_7d` on the response comes from `context.author_pr_events_7d`, not from a signal.

## How to go through it

### 1. Prove the key and lock the model ids (about 25 minutes)

Fill `MODEL_ACCESS_KEY` in `.env`. From the repo root:

```powershell
.\.venv\Scripts\python.exe -c "import os; from dotenv import load_dotenv; from openai import OpenAI; load_dotenv(); c = OpenAI(base_url='https://inference.do-ai.run/v1', api_key=os.environ['MODEL_ACCESS_KEY']); print('\n'.join(sorted(m.id for m in c.models.list().data)))"
```

Write two ids into `.env`:

- `SMALL_MODEL`: smallest instruct model that follows JSON, around the 7B–8B class.
- `LARGE_MODEL`: a clearly larger open model on the same endpoint.

Send one chat completion with `temperature=0` and `max_completion_tokens=64`. A normal text reply means the key, the id, and the base URL are good. Post both ids in the group chat so the README can name them.

### 2. One hardcoded pull request returns valid JSON (until about 12:30)

Edit `rubric.md` so the required model JSON is exactly:

```json
{
  "verdict": "ship_it | needs_work | likely_spam",
  "confidence": 0.0,
  "evidence": [{"signal": "has_tests", "detail": "no test file among 3 changed files"}],
  "contributor_reply": "Thanks for opening this. Add a test for path/to/file.py.",
  "maintainer_summary": "Real attempt, no tests, no linked issue."
}
```

Keep the verdict rules already in that file. The reply names a file or a missing piece and never uses the word spam. Confidence below 0.6 means the case is ambiguous.

In `prism/judge.py`, add these helpers, then `judge`:

1. `load_rubric()` reads `skill/prism-triage/references/rubric.md`. Repo root is `Path(__file__).resolve().parents[1]`.
2. `build_user_payload(pr, signals, context)` returns one JSON string. Truncate `pr.body` to 2,000 characters. Send at most 20 filenames and the first 500 characters of each patch. Include every signal’s `signal`, `detail`, and `value`, plus `author_pr_events_7d` and `repo_pr_events_7d`. Stop once the payload reaches about 8,000 characters.
3. `parse_json(text)` strips a leading ` ```json ` fence when present, then `json.loads`.

Call the small model:

```python
client = OpenAI(
    base_url="https://inference.do-ai.run/v1",
    api_key=os.environ["MODEL_ACCESS_KEY"],
)
resp = client.chat.completions.create(
    model=os.environ["SMALL_MODEL"],
    temperature=0,
    max_completion_tokens=800,
    messages=[
        {"role": "system", "content": load_rubric()},
        {"role": "user", "content": payload},
    ],
)
text = resp.choices[0].message.content or ""
```

Validate `verdict` against `ship_it | needs_work | likely_spam`, `confidence` in 0..1, and `evidence` as a list of `{signal, detail}`. On `JSONDecodeError` or `ValidationError`, append the bad assistant text and a user message: `Validation failed: <error>. Return only corrected JSON.` Call again. Stop after two repairs. If it is still invalid, raise `RuntimeError`.

Build `TriageResponse` in Python:

- From the model: `verdict`, `confidence`, `evidence`, `contributor_reply`, `maintainer_summary`.
- From the `signals` argument: `Signals`. Map `size` to `lines_changed` (fall back to `pr.additions + pr.deletions`), and copy `has_tests`, `linked_issue`, `followed_contributing`. Set `author_pr_velocity_7d` from `context.author_pr_events_7d`.
- From the call: `model_used` is the id that produced the final text. `escalated` is false in this step. `cost_usd` is `(prompt_tokens / 1_000_000) * input_rate + (completion_tokens / 1_000_000) * output_rate`, using the small-model rates. Add every repair call into that total. `pr_url` is `pr.url`. `snowflake_context` is the `context` argument, unchanged.

Add a `main` block with two fakes:

- Spam: title `add my name to README`, one whitespace patch, `SnowflakeContext(author_pr_events_7d=14, repo_pr_events_7d=2, dataset="fixture", source="cache")`.
- Real attempt: a file `tests/test_app.py` and body `Fixes #12`.

```powershell
.\.venv\Scripts\python.exe -m prism.judge
```

Done when the spam fake returns `likely_spam` or `needs_work`, and the JSON validates as `TriageResponse`.

### 3. Give Rohith the real function (by 1:15)

Keep this signature:

```python
def judge(
    pr: PullRequest,
    signals: list[Signal],
    context: SnowflakeContext,
    escalate: bool = True,
) -> TriageResponse:
```

`escalate` defaults to true so Rohith can call `judge(pr, signals, context)` with no extra arguments. He replaces the mock in `prism/api.py` with:

```python
pr = fetch_pr(body.pr_url)
signals = extract_signals(pr)
context = repo_context(pr.author, f"{pr.owner}/{pr.repo}")
return judge(pr, signals, context)
```

He wraps `judge` in `try/except RuntimeError` and returns the error text. He does not rebuild `signals` or `snowflake_context`.

If Diveet’s functions still raise `NotImplementedError` at 1:15, Rohith leaves the HTTP mock in place and Manthan keeps testing through `python -m prism.judge`.

### 4. Cascade (1:15–2:15)

After a valid small-model result, escalate when `escalate` is true and any of these holds:

- `confidence < 0.6`
- verdict is `ship_it` and a signal named `whitespace_only` has value `True`
- verdict is `ship_it`, `author_pr_events_7d >= 10`, and `pr.additions + pr.deletions <= 5`

The second call uses `LARGE_MODEL` and the large-model prices. On success, set `escalated=True`, `model_used` to the large id, and add both calls into `cost_usd`. Copy the same `signals` and `snowflake_context` as on the small result.

If the large model raises after its two repairs, return the small-model object with `escalated=True` and append the large-model error to `maintainer_summary`.

Check the two fakes again. Both should stay on the small model when it is confident: a sure `likely_spam` and a sure `ship_it` with tests and a linked issue match no rule. Escalation is for the ambiguous middle, so check that path by forcing `ESCALATE_BELOW` above 1.0 once.

### 5. Measure (2:15–2:45)

Implement `eval/run_eval.py`. Read `eval/labeled.csv` with the `csv` module and skip blank rows.

For each `pr_url`, build inputs in this order:

1. If `fetch_pr`, `extract_signals`, and `repo_context` import and run, use them.
2. If they still raise, score 6 to 8 hand-built cases in the `main` path and write in the printed header that the score is on fixtures. A fixture score can go on the slide. An empty run cannot.

Call `judge(..., escalate=False)` and `judge(...)` for every row. A row is correct when `verdict` equals `human_verdict`. Print:

```text
small-only  11/15  mean cost $0.0003
cascade     13/15  mean cost $0.0005
```

If the small model misses most rows, edit `rubric.md` once and rerun. Do not retune after 2:45. Send the two lines to Chahat for the README and the pitch.

### 6. Freeze (2:45–3:15)

No new response fields. Be ready to answer, in this order: the two model ids and why they are open-weight, the three escalation rules, how many labeled rows, and the two cost lines. The cascade plus the validate-and-retry loop is the original harness. The rubric inside the skill is his, even though Rohith owns `SKILL.md`.

## Done

- `.env` has two open-weight ids and four prices, and `.env` is not committed.
- `python -m prism.judge` prints a valid `TriageResponse` for the spam fake, with real signal values and the Snowflake context that were passed in.
- Confident fakes stay on the small model. A forced low threshold routes to the large model and adds both calls into `cost_usd`.
- A small-model failure after two repairs raises `RuntimeError`. A large-model failure falls back to the small result.
- `eval/run_eval.py` prints `correct/total` and mean cost for small-only and cascade.
- `api.py` returns `judge(...)` without overwriting `signals` or `snowflake_context`.
