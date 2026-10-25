"""Evidence Bundle construction and the Evidence Receipt (F-005).

A bundle is the factual shared state between the deterministic core and the AI
layer. It is built only from validated events and reproducible metrics, and its
interpreted section starts deliberately empty.
"""

from __future__ import annotations

from src.models.event import Event
from src.models.insight import (
    DerivedEvidence,
    Detection,
    DetectorConfig,
    DetectorEvidence,
    EvidenceBundle,
    InterpretedEvidence,
    ObservedEvidence,
)


def build_evidence_bundle(
    detection: Detection,
    events: list[Event],
    config: DetectorConfig | None = None,
) -> EvidenceBundle:
    """Turn a detection into an auditable bundle.

    Only events that actually fall inside the current window are referenced, and
    only events belonging to the detecting team count as supporting evidence.
    """

    config = config or DetectorConfig()
    comparison = detection.comparison
    start, end = comparison.current.start_second, comparison.current.end_second

    window_events = [e for e in events if start <= e.match_seconds < end]
    team_events = [e for e in window_events if e.team_id == detection.team_id]

    event_counts: dict[str, int] = {}
    for event in window_events:
        key = f"{event.team_id}:{event.event_type}:{event.outcome}"
        event_counts[key] = event_counts.get(key, 0) + 1

    return EvidenceBundle(
        insight_id=detection.insight_id,
        match_id=detection.match_id,
        team_id=detection.team_id,  # type: ignore[arg-type]
        type=detection.type,
        window_start_second=start,
        window_end_second=end,
        window_start_minute=comparison.current.start_minute,
        window_end_minute=comparison.current.end_minute,
        observed=ObservedEvidence(
            event_counts=event_counts,
            event_ids=[e.event_id for e in team_events],
        ),
        derived=DerivedEvidence(
            previous_metrics=comparison.previous,
            current_metrics=comparison.current,
            deltas={
                "possession_share": comparison.possession_share_delta,
                "progressive_passes": float(comparison.progressive_passes_delta),
                "final_third_entries": float(comparison.final_third_entries_delta),
                "shots": float(comparison.shots_delta),
                "threat_added": comparison.threat_added_delta,
                "recoveries": float(comparison.recoveries_delta),
                "control_score": comparison.control_score_delta,
            },
            control_score_change=comparison.control_score_delta,
            confidence=detection.confidence,
            confidence_breakdown=detection.confidence_breakdown,
        ),
        detector=DetectorEvidence(
            config=config,
            triggered_signals=[s for s in detection.signals if s.triggered],
            algorithm_version=detection.algorithm_version,
            cooldown_metadata={
                "detected_at_second": detection.detected_at_second,
                "cooldown_until_second": detection.cooldown_until_second,
            },
        ),
        interpreted=InterpretedEvidence(),
        verification_status="pending",
    )


def evidence_receipt(bundle: EvidenceBundle) -> dict:
    """The 'Why did MatchSense say this?' view, human- and UI-readable."""

    derived = bundle.derived
    triggered = bundle.detector.triggered_signals

    return {
        "insight_id": bundle.insight_id,
        "window": {
            "start_minute": bundle.window_start_minute,
            "end_minute": bundle.window_end_minute,
            "start_second": bundle.window_start_second,
            "end_second": bundle.window_end_second,
        },
        "claim": bundle.interpreted.claim or "not yet interpreted",
        "truth_layers": {
            "observed": {
                "event_count": len(bundle.observed.event_ids),
                "event_ids": bundle.observed.event_ids,
            },
            "derived": {
                "control_score_before": derived.previous_metrics.control_score,
                "control_score_after": derived.current_metrics.control_score,
                "control_score_change": derived.control_score_change,
                "confidence": derived.confidence,
                "confidence_breakdown": derived.confidence_breakdown,
                "deltas": derived.deltas,
            },
            "interpreted": {
                "claim": bundle.interpreted.claim,
                "significance": bundle.interpreted.significance,
                "critic_decision": bundle.interpreted.critic_decision,
                "critic_reason": bundle.interpreted.critic_reason,
                "rejected_claim": bundle.interpreted.rejected_claim,
            },
        },
        "signals": [
            {
                "name": signal.name,
                "previous": signal.previous_value,
                "current": signal.current_value,
                "delta": signal.delta,
                "threshold": signal.threshold,
            }
            for signal in triggered
        ],
        "algorithm_version": bundle.detector.algorithm_version,
        "verification_status": bundle.verification_status,
        "cooldown": bundle.detector.cooldown_metadata,
    }
