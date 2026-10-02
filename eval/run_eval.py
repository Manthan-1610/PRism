"""Accuracy and cost on eval/labeled.csv. Manthan owns this file.

Read pr_url,human_verdict,notes.
Call the judge twice per row if needed: small-only, then the cascade.
A row is correct when verdict equals human_verdict.
Print correct/total and mean cost_usd for each mode.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    csv_path = ROOT / "eval" / "labeled.csv"
    raise NotImplementedError(f"Manthan: score {csv_path}")


if __name__ == "__main__":
    main()
