"""CLI entry for the agent skill.

Usage from the repo root:
    python skill/prism-triage/scripts/triage.py <pr_url>
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python skill/prism-triage/scripts/triage.py <pr_url>", file=sys.stderr)
        raise SystemExit(2)

    from prism.context import repo_context
    from prism.ingest import fetch_pr
    from prism.judge import judge
    from prism.signals import extract_signals

    try:
        pr = fetch_pr(sys.argv[1])
        signals = extract_signals(pr)
        context = repo_context(pr.author, f"{pr.owner}/{pr.repo}")
        result = judge(pr, signals, context)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
