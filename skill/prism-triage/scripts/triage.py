"""CLI entry for the agent skill. Rohith owns the wiring.

Usage from the repo root:
    python skill/prism-triage/scripts/triage.py <pr_url>
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python skill/prism-triage/scripts/triage.py <pr_url>", file=sys.stderr)
        raise SystemExit(1)
    pr_url = sys.argv[1]

    from prism.api import triage
    from prism.contract import TriageRequest

    try:
        response = triage(TriageRequest(pr_url=pr_url))
        print(response.model_dump_json(indent=2))
    except Exception as exc:
        print(json.dumps({"error": getattr(exc, "detail", str(exc))}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
