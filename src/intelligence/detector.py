"""Control-shift detector and deterministic confidence (F-004).

Emits a detection only when *combined* evidence passes configured thresholds,
which keeps single-event noise out of the UI.
"""

from __future__ import annotations

from src.features.windows import timeline_endpoints, compare_windows
from src.intelligence.rules import has_real_baseline
from src.models.event import Event
from src.models.insight import (
    Detection,
    DetectorConfig,
    Signal,
    WindowComparison,
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def build_signals(comparison: WindowComparison, config: DetectorConfig) -> list[Signal]:
    c = comparison
    specs = [
        ("possession_share", "possession_share_delta", c.possession_share_delta, config.possession_signal_delta),
        ("progressive_passes", "progressive_passes_delta", c.progressive_passes_delta, config.progressive_signal_delta),
        ("final_third_entries", "final_third_entries_delta", c.final_third_entries_delta, config.final_third_signal_delta),
        ("shots", "shots_delta", c.shots_delta, config.shots_signal_delta),
        ("threat", "threat_added_delta", c.threat_added_delta, config.threat_signal_delta),
        ("recoveries", "recoveries_delta", c.recoveries_delta, config.recovery_signal_delta),
    ]
    signals: list[Signal] = []
    for name, metric, delta, threshold in specs:
        previous_value = getattr(c.previous, metric.replace("_delta", ""))
        current_value = getattr(c.current, metric.replace("_delta", ""))
        signals.append(
            Signal(
                name=name,
                metric=metric,
                previous_value=float(previous_value),
                current_value=float(current_value),
                delta=float(delta),
                threshold=float(threshold),
                triggered=delta >= threshold,
            )
        )
    return signals


def compute_confidence(
    signals: list[Signal],
    comparison: WindowComparison,
    config: DetectorConfig,
) -> tuple[float, dict[str, float]]:
    """Deterministic confidence: strength, agreement, persistence, sufficiency."""

    triggered = [s for s in signals if s.triggered]
    if not triggered:
        breakdown = {"signal_strength": 0.0, "agreement": 0.0, "persistence": 0.0, "sample": 0.0}
        return 0.0, breakdown

    # 1. strength: mean normalised overshoot of the triggered signals
    strength = sum(
        _clamp((s.delta - s.threshold) / max(s.threshold, 1e-9) + 1.0, 0.0, 2.0) / 2.0
        for s in triggered
    ) / len(triggered)

    # 2. agreement: how many independent signals point the same way
    agreement = _clamp(len(triggered) / max(config.minimum_signals * 2, 1))

    # 3. persistence: repeated detections are handled by the caller; a single
    #    window counts as 1/persistence_windows of the persistence term
    persistence = _clamp(1.0 / max(config.persistence_windows, 1) + 0.25)

    # 4. sample sufficiency: is there enough activity to trust the deltas?
    support = max(len(comparison.current.supporting_event_ids), 1)
    sample = _clamp(support / max(config.minimum_supporting_events, 1))

    breakdown = {
        "signal_strength": round(strength, 4),
        "agreement": round(agreement, 4),
        "persistence": round(persistence, 4),
        "sample": round(sample, 4),
    }
    confidence = (
        0.35 * strength + 0.25 * agreement + 0.20 * persistence + 0.20 * sample
    )
    return round(_clamp(confidence), 4), breakdown


def is_candidate(
    signals: list[Signal], comparison: WindowComparison, config: DetectorConfig
) -> bool:
    triggered = [s for s in signals if s.triggered]
    return (
        comparison.control_score_delta >= config.control_score_threshold
        and len(triggered) >= config.minimum_signals
        and len(comparison.current.supporting_event_ids) >= config.minimum_supporting_events
        and comparison.current.event_count >= config.minimum_window_events
    )


class ControlShiftDetector:
    """Scans a match chronologically and returns ordered detections."""

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()

    def detect(self, events: list[Event], match_id: str) -> list[Detection]:
        detections: list[Detection] = []
        cooldown_until = {("HOME",): 0, ("AWAY",): 0}
        counter = 0

        for end_second in timeline_endpoints(events):
            for team in ("HOME", "AWAY"):
                comparison = compare_windows(events, end_second, team)
                if not has_real_baseline(comparison, self.config):
                    continue
                signals = build_signals(comparison, self.config)
                if not is_candidate(signals, comparison, self.config):
                    continue
                if end_second < cooldown_until[(team,)]:
                    continue

                confidence, breakdown = compute_confidence(signals, comparison, self.config)
                counter += 1
                cooldown_until[(team,)] = end_second + self.config.cooldown_seconds
                detections.append(
                    Detection(
                        insight_id=f"INS-{counter:03d}",
                        match_id=match_id,
                        team_id=team,  # type: ignore[arg-type]
                        start_minute=comparison.current.start_minute,
                        end_minute=comparison.current.end_minute,
                        detected_at_second=end_second,
                        comparison=comparison,
                        signals=signals,
                        triggered_signal_names=[s.name for s in signals if s.triggered],
                        control_score_delta=comparison.control_score_delta,
                        confidence=confidence,
                        confidence_breakdown=breakdown,
                        supporting_event_ids=comparison.current.supporting_event_ids,
                        cooldown_until_second=cooldown_until[(team,)],
                    )
                )
        return detections
