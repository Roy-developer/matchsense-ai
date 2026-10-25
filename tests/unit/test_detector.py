"""Detector, confidence and cooldown tests (F-004)."""

from __future__ import annotations

import pytest

from src.features.windows import compare_windows
from src.intelligence.detector import (
    ControlShiftDetector,
    build_signals,
    compute_confidence,
    is_candidate,
)
from src.models.insight import DetectorConfig


def test_detector_finds_the_injected_scenario(golden_models):
    detections = ControlShiftDetector().detect(golden_models, "MATCH-001")
    assert detections, "detector produced no insights for a match with injected surges"

    # the scripted home control shift runs 55-68'
    overlapping = [
        d for d in detections if d.team_id == "HOME" and d.end_minute >= 55 and d.start_minute <= 68
    ]
    assert overlapping, "scripted home control shift was not detected"


def test_detections_are_positive_control_shifts(golden_models):
    config = DetectorConfig()
    for detection in ControlShiftDetector(config).detect(golden_models, "MATCH-001"):
        assert detection.control_score_delta >= config.control_score_threshold
        assert len(detection.triggered_signal_names) >= config.minimum_signals


def test_confidence_is_bounded_and_deterministic(golden_models):
    first = ControlShiftDetector().detect(golden_models, "MATCH-001")
    second = ControlShiftDetector().detect(golden_models, "MATCH-001")
    assert [d.model_dump() for d in first] == [d.model_dump() for d in second]
    for detection in first:
        assert 0.0 <= detection.confidence <= 1.0


def test_cooldown_suppresses_duplicate_detections(golden_models):
    detections = ControlShiftDetector().detect(golden_models, "MATCH-001")
    by_team: dict[str, list] = {}
    for detection in detections:
        by_team.setdefault(detection.team_id, []).append(detection)

    for team, team_detections in by_team.items():
        ordered = sorted(team_detections, key=lambda d: d.detected_at_second)
        for earlier, later in zip(ordered, ordered[1:]):
            assert later.detected_at_second >= earlier.cooldown_until_second, (
                f"{team} fired twice inside one cooldown window"
            )


def test_quiet_match_produces_no_detections():
    assert ControlShiftDetector().detect([], "MATCH-EMPTY") == []


def test_single_signal_is_not_enough(golden_models):
    config = DetectorConfig(minimum_signals=2)
    comparison = compare_windows(golden_models, 3600, "HOME")
    signals = build_signals(comparison, config)
    strong = [s for s in signals if s.triggered]

    if len(strong) >= 2:
        # pretend only one signal fired
        trimmed = [s.model_copy(update={"triggered": s is strong[0]}) for s in signals]
        assert not is_candidate(trimmed, comparison, config)


def test_confidence_is_zero_without_signals(golden_models):
    config = DetectorConfig()
    comparison = compare_windows(golden_models, 3600, "HOME")
    silent = [s.model_copy(update={"triggered": False}) for s in build_signals(comparison, config)]
    confidence, breakdown = compute_confidence(silent, comparison, config)
    assert confidence == 0.0
    assert all(value == 0.0 for value in breakdown.values())


def test_thresholds_are_configurable(golden_models):
    strict = DetectorConfig(control_score_threshold=0.95)
    lenient = DetectorConfig(control_score_threshold=0.01)

    assert len(ControlShiftDetector(strict).detect(golden_models, "MATCH-001")) <= len(
        ControlShiftDetector(lenient).detect(golden_models, "MATCH-001")
    )


def test_detection_carries_provenance(golden_models):
    detections = ControlShiftDetector().detect(golden_models, "MATCH-001")
    assert detections
    valid_ids = {e.event_id for e in golden_models}
    for detection in detections:
        assert detection.supporting_event_ids
        assert set(detection.supporting_event_ids).issubset(valid_ids)
        assert detection.algorithm_version
        assert detection.data_version


def test_signals_record_before_and_after(golden_models):
    detection = ControlShiftDetector().detect(golden_models, "MATCH-001")[0]
    for signal in detection.signals:
        assert signal.previous_value >= 0
        assert signal.current_value >= 0
        assert pytest.approx(signal.delta, abs=1e-9) == signal.current_value - signal.previous_value
