"""One-command vertical slice: MATCH-001 -> detection -> verified receipt.

    python -m scripts.run_demo
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import receipt_payload, run_pipeline_from_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MatchSense evidence pipeline end to end")
    parser.add_argument("--data", default="data/synthetic")
    parser.add_argument("--match-id", default="MATCH-001")
    parser.add_argument("--max-insights", type=int, default=None)
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args()

    run = run_pipeline_from_dir(args.data, args.match_id, max_insights=args.max_insights)
    receipts = receipt_payload(run)

    if args.json:
        print(json.dumps({"summary": run.summary(), "receipts": receipts}, indent=2))
        return 0

    summary = run.summary()
    print("=" * 72)
    print(f"{summary['home_team']} {summary['score']} {summary['away_team']}")
    print(
        f"events {summary['events']} | detections {summary['detections']} | "
        f"approved {summary['approved']} | rejected {summary['rejected']} | "
        f"provider {summary['provider']}"
    )
    print("=" * 72)

    for insight, receipt in zip(run.insights, receipts):
        detection = insight.detection
        header = (
            f"{receipt['insight_id']}  {detection.team_id}  "
            f"{receipt['window']['start_minute']:.0f}-{receipt['window']['end_minute']:.0f}'  "
            f"confidence {receipt['truth_layers']['derived']['confidence']:.2f}"
        )
        print(f"\n{header}")

        if insight.verified:
            print(f"  OBSERVED   {len(receipt['truth_layers']['observed']['event_ids'])} events "
                  f"in window (ids {receipt['truth_layers']['observed']['event_ids'][0]}.."
                  f"{receipt['truth_layers']['observed']['event_ids'][-1]})")
            print(f"  DERIVED    control score "
                  f"{receipt['truth_layers']['derived']['control_score_before']:.2f} -> "
                  f"{receipt['truth_layers']['derived']['control_score_after']:.2f}")
            print(f"  SIGNALS    {', '.join(s['name'] for s in receipt['signals'])}")
            print(f"  APPROVED   {insight.verified.claim}")
            for audience in ("fan", "analyst", "broadcast"):
                narrative = insight.narratives.get(audience)
                if narrative:
                    print(f"    [{audience:9}] {narrative.headline} - {narrative.body}")
        else:
            print(f"  REJECTED   {insight.rejected_claim}")
            print(f"  REASON     {insight.critic_reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
