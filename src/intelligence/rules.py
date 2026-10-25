"""Signals, confidence and candidate rules shared by the detector and pipeline."""

from __future__ import annotations

from src.models.insight import Detection, DetectorConfig, WindowComparison


def has_real_baseline(comparison: WindowComparison, config: DetectorConfig) -> bool:
    """A shift can only be claimed against a window that actually has data.

    Comparing the first five minutes against an empty pre-match window would
    manufacture a "shift" out of the start of the match, so those are skipped.
    """

    return comparison.previous.event_count >= config.minimum_window_events


def has_meaningful_change(detection: Detection) -> bool:
    """At least one triggered signal must be a real change, not a 0 -> 0 artefact."""

    return any(
        signal.triggered and signal.current_value != signal.previous_value
        for signal in detection.signals
    )
