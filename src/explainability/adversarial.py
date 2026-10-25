"""Adversarial demonstration: claims that must be rejected (AI-002 evidence).

The guide's headline differentiator is that MatchSense refuses to publish
unsupported claims, so the demo has to *show* a rejection rather than only
assert that one happened.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.narrative.pipeline import resolve_claim

if TYPE_CHECKING:  # avoids a circular import at runtime
    from src.pipeline import MatchRun

ADVERSARIAL_ATTEMPTS: list[tuple[str, str]] = [
    (
        "Formation claim (not present in event data)",
        "The home side switched to a 4-3-3 and pushed their full-backs higher",
    ),
    (
        "Invented statistics",
        "The home side had 97 percent possession and 42 shots in this spell",
    ),
    (
        "Fatigue claim (not observable from events)",
        "The away side were visibly tired after a demanding week",
    ),
]


def adversarial_demo(run: "MatchRun") -> list[dict]:
    """Feed the Critic claims it must block, and record the reasons."""

    if not run.insights:
        return []

    bundle = run.insights[0].bundle
    results = []
    for label, claim in ADVERSARIAL_ATTEMPTS:
        verified, result = resolve_claim(bundle, claim, "This changed the game.")
        results.append(
            {
                "case": label,
                "claim": claim,
                "status": result.status,
                "reasons": result.reasons,
                "blocked": verified is None,
            }
        )
    return results
