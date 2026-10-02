"""Accuracy and cost on eval/labeled.csv, small-only versus cascade.

Rows are scored live through fetch_pr, extract_signals, and repo_context.
If those are not implemented yet, or the CSV has no rows, the built-in
fixture cases in prism.judge are scored instead and the header says so.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prism.judge import _fake_cases, judge  # noqa: E402

CSV_PATH = ROOT / "eval" / "labeled.csv"
FIXTURE_LABELS = {"spam": "likely_spam", "real": "ship_it"}


def load_rows() -> list[dict]:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if (r.get("pr_url") or "").strip()]


def live_cases(rows: list[dict]) -> list[tuple[str, str, object, list, object]]:
    from prism.context import repo_context
    from prism.ingest import fetch_pr
    from prism.signals import extract_signals

    cases = []
    for row in rows:
        url = row["pr_url"].strip()
        try:
            pr = fetch_pr(url)
            signals = extract_signals(pr)
            context = repo_context(pr.author, f"{pr.owner}/{pr.repo}")
        except NotImplementedError:
            raise
        except Exception as exc:
            print(f"skip {url}: {exc}")
            continue
        cases.append((url, row["human_verdict"].strip(), pr, signals, context))
    return cases


def fixture_cases() -> list[tuple[str, str, object, list, object]]:
    return [(name, FIXTURE_LABELS[name], pr, sigs, ctx) for name, pr, sigs, ctx in _fake_cases()]


def score(cases, escalate: bool) -> tuple[int, float, int]:
    correct = 0
    cost = 0.0
    escalated = 0
    for name, label, pr, signals, context in cases:
        try:
            result = judge(pr, signals, context, escalate=escalate)
        except RuntimeError as exc:
            print(f"  {name}: judge failed: {exc}")
            continue
        correct += result.verdict == label
        cost += result.cost_usd
        escalated += result.escalated
        mark = "ok " if result.verdict == label else "MISS"
        print(f"  {mark} {name}: {result.verdict} (label {label}, {result.model_used}, conf {result.confidence:.2f})")
    return correct, cost, escalated


def main() -> None:
    rows = load_rows()
    source = "labeled.csv"
    try:
        cases = live_cases(rows) if rows else []
    except NotImplementedError:
        cases = []
    if not cases:
        source = "built-in fixtures (labeled.csv empty or pipeline not ready)"
        cases = fixture_cases()

    print(f"Scoring {len(cases)} cases from {source}")
    results = {}
    for mode, escalate in (("small-only", False), ("cascade", True)):
        print(mode)
        results[mode] = score(cases, escalate)

    total = len(cases)
    print()
    for mode, (correct, cost, escalated) in results.items():
        mean = cost / total if total else 0.0
        print(f"{mode:<11} {correct}/{total}  mean cost ${mean:.4f}  escalated {escalated}")


if __name__ == "__main__":
    main()
