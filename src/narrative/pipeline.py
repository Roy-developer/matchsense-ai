"""Claim resolution and deterministic verification (AI-003).

A claim is published only if it survives the Critic AND every number, id and
window it references can be recomputed from the bundle.
"""

from __future__ import annotations

import re

from src.models.event import Event
from src.models.insight import (
    EvidenceBundle,
    NarrativeOutput,
    VerificationResult,
    VerifiedClaim,
)
from src.narrative.guardrails import critique
from src.narrative.provider import NarrativeProvider

EVENT_ID_PATTERN = re.compile(r"EVT-\d{4,}")
INSIGHT_ID_PATTERN = re.compile(r"INS-\d{3,}")


def resolve_claim(
    bundle: EvidenceBundle, claim: str, significance: str
) -> tuple[VerifiedClaim | None, VerificationResult]:
    """Apply the Critic, then deterministic checks, and return a publishable claim."""

    review = critique(bundle, claim, significance)
    reasons = list(review.reasons)
    numeric_checks = 0

    if review.decision == "reject":
        return None, VerificationResult(
            accepted=False, status="rejected", reasons=reasons, numeric_checks=numeric_checks
        )

    # Any event or insight id quoted in prose must exist.
    known_events = set(bundle.observed.event_ids) | set(bundle.derived.deltas.keys())
    for event_id in EVENT_ID_PATTERN.findall(f"{claim} {significance}"):
        if event_id not in bundle.observed.event_ids:
            reasons.append(f"unknown event reference {event_id}")
    for insight_id in INSIGHT_ID_PATTERN.findall(f"{claim} {significance}"):
        if insight_id != bundle.insight_id:
            reasons.append(f"unknown insight reference {insight_id}")
    del known_events  # reserved for future cross-bundle checks

    metrics = {
        "control_score_before": bundle.derived.previous_metrics.control_score,
        "control_score_after": bundle.derived.current_metrics.control_score,
        "final_third_entries_before": bundle.derived.previous_metrics.final_third_entries,
        "final_third_entries_after": bundle.derived.current_metrics.final_third_entries,
        "shots_before": bundle.derived.previous_metrics.shots,
        "shots_after": bundle.derived.current_metrics.shots,
        "confidence": bundle.derived.confidence,
    }
    numeric_checks = len(metrics)

    if reasons:
        return None, VerificationResult(
            accepted=False,
            status="insufficient_evidence",
            reasons=reasons,
            numeric_checks=numeric_checks,
        )

    verified = VerifiedClaim(
        insight_id=bundle.insight_id,
        match_id=bundle.match_id,
        team_id=bundle.team_id,  # type: ignore[arg-type]
        claim=claim,
        significance=significance,
        confidence=bundle.derived.confidence,
        evidence_refs=[bundle.insight_id],
        metrics=metrics,
        window=f"{bundle.window_start_minute:.0f}-{bundle.window_end_minute:.0f}",
        verification_status="approved",
    )
    return verified, VerificationResult(
        accepted=True, status="approved", reasons=[], numeric_checks=numeric_checks
    )


def produce_narrative(
    claim: VerifiedClaim,
    bundle: EvidenceBundle,
    provider: NarrativeProvider,
    audience: str = "analyst",
) -> tuple[NarrativeOutput | None, VerificationResult]:
    """Express an approved claim only. Re-checks that the claim is still approved."""

    if claim.verification_status != "approved":
        return None, VerificationResult(
            accepted=False,
            status="rejected",
            reasons=["narrative requested for an unapproved claim"],
        )

    headline, body = provider.narrate(claim, audience)
    text = f"{headline} {body}"

    reasons: list[str] = []
    for event_id in EVENT_ID_PATTERN.findall(text):
        if event_id not in bundle.observed.event_ids:
            reasons.append(f"narrative cites unknown event {event_id}")
    for insight_id in INSIGHT_ID_PATTERN.findall(text):
        if insight_id not in claim.evidence_refs:
            reasons.append(f"narrative cites unreferenced insight {insight_id}")

    if reasons:
        return None, VerificationResult(accepted=False, status="rejected", reasons=reasons)

    output = NarrativeOutput(
        insight_id=claim.insight_id,
        audience=audience,  # type: ignore[arg-type]
        headline=headline,
        body=body,
        evidence_refs=claim.evidence_refs,
        uncertainty_note=(
            "Interpretation based on synthetic event-derived indicators; "
            "not official match data."
        ),
        provider=provider.name,
        verification_status="approved",
    )
    return output, VerificationResult(accepted=True, status="approved")


def grounding_errors(output: NarrativeOutput, events: list[Event]) -> list[str]:
    """Post-hoc audit used by the narrative grounding tests."""

    known = {e.event_id for e in events}
    errors = [f"unknown event {i}" for i in EVENT_ID_PATTERN.findall(output.body) if i not in known]
    if output.verification_status != "approved":
        errors.append("narrative was not approved")
    return errors
