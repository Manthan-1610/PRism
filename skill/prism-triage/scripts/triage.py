"""CLI entry for the agent skill. Rohith owns the wiring.

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
    pr_url = sys.argv[1]
    # from prism.ingest import fetch_pr
    # from prism.signals import extract_signals
    # from prism.context import repo_context
    # from prism.judge import judge
    # pr = fetch_pr(pr_url)
    # signals = extract_signals(pr)
    # context = repo_context(pr.author, f"{pr.owner}/{pr.repo}")
    # print(judge(pr, signals, context).model_dump_json(indent=2))
    print(f"not implemented yet: {pr_url}")


if __name__ == "__main__":
    main()
