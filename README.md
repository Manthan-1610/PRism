# PRism

Triage a public GitHub pull request with deterministic checks, a Snowflake GitHub-events query, and an open-weight model cascade.

This tree is a stub. Each module raises `NotImplementedError` until that owner fills it in. `POST /triage` currently returns the example contract so the UI can be built in parallel.

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
