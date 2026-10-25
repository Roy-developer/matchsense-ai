"""Generate the deterministic synthetic match (F-002).

    python -m scripts.generate_match
    python -m scripts.generate_match --seed 20261023 --out data
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.generator import DEFAULT_SEED, write_match  # noqa: E402
from src.data.loader import load_match  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the deterministic MatchSense synthetic match")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--match-id", default="MATCH-001")
    parser.add_argument("--out", default="data/synthetic")
    args = parser.parse_args()

    jsonl, meta = write_match(args.out, seed=args.seed, match_id=args.match_id)
    events, metadata, validation = load_match(args.out, args.match_id)

    print(f"events     : {len(events)} -> {jsonl}")
    print(f"metadata   : {meta}")
    print(f"score      : {metadata.home_team} {metadata.home_goals} - {metadata.away_goals} {metadata.away_team}")
    print(f"validation : {'VALID' if validation.valid else 'INVALID'}")
    for error in validation.errors:
        print(f"  error: {error}")
    for warning in validation.warnings:
        print(f"  warning: {warning}")
    return 0 if validation.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
