"""Rolling-window feature tests (F-003)."""

from __future__ import annotations

from src.features.metrics import (
    is_final_third_entry,
    is_penalty_area_entry,
    is_progressive,
    is_recovery,
    xg_proxy,
)
from src.features.windows import (
    compare_windows,
    compute_window,
    timeline_endpoints,
    window_bounds,
)
from src.models.event import Event


def test_window_bounds_are_contiguous():
    start, end = window_bounds(600)
    assert (start, end) == (300, 600)


def test_window_bounds_never_go_negative():
    assert window_bounds(100) == (0, 100)


def test_compare_windows_uses_previous_as_neighbour(golden_models):
    comparison = compare_windows(golden_models, 3600, "HOME")
    assert comparison.current.start_second == comparison.previous.end_second
    assert (comparison.previous.start_second, comparison.previous.end_second) == (3000, 3300)
    assert (comparison.current.start_second, comparison.current.end_second) == (3300, 3600)


def test_every_window_in_golden_match_has_events(golden_models):
    for end in timeline_endpoints(golden_models):
        window = compute_window(golden_models, end, "HOME")
        assert window.event_count > 0, f"empty window ending at {end}s"


def test_possession_shares_sum_to_one(golden_models):
    for end in timeline_endpoints(golden_models):
        home = compute_window(golden_models, end, "HOME")
        away = compute_window(golden_models, end, "AWAY")
        if home.event_count:
            total = home.possession_share + away.possession_share
            assert abs(total - 1.0) < 1e-6


def test_pass_completion_is_bounded(golden_models):
    for end in timeline_endpoints(golden_models):
        window = compute_window(golden_models, end, "HOME")
        assert 0.0 <= window.pass_completion_pct <= 100.0
        assert window.passes_completed <= window.passes_attempted


def test_counts_are_source_derived(golden_models):
    """Every count must equal a filter over the events in that window."""

    window = compute_window(golden_models, 3600, "HOME")
    team_events = [
        e
        for e in golden_models
        if window.start_second <= e.match_seconds < window.end_second and e.team_id == "HOME"
    ]
    assert window.event_count == len(
        [e for e in golden_models if window.start_second <= e.match_seconds < window.end_second]
    )
    assert window.supporting_event_ids == [e.event_id for e in team_events]
    assert window.passes_attempted == sum(1 for e in team_events if e.event_type == "pass")
    assert window.shots == sum(1 for e in team_events if e.event_type == "shot")
    assert window.final_third_entries == sum(1 for e in team_events if is_final_third_entry(e))


def test_control_score_is_bounded(golden_models):
    for end in timeline_endpoints(golden_models):
        window = compute_window(golden_models, end, "HOME")
        assert 0.0 <= window.control_score <= 1.0


def test_deltas_equal_current_minus_previous(golden_models):
    comparison = compare_windows(golden_models, 3600, "HOME")
    assert comparison.shots_delta == comparison.current.shots - comparison.previous.shots
    assert (
        comparison.final_third_entries_delta
        == comparison.current.final_third_entries - comparison.previous.final_third_entries
    )
    assert abs(
        comparison.control_score_delta
        - (comparison.current.control_score - comparison.previous.control_score)
    ) < 1e-6


def test_metrics_are_deterministic(golden_models):
    first = compare_windows(golden_models, 3600, "HOME")
    second = compare_windows(golden_models, 3600, "HOME")
    assert first.model_dump() == second.model_dump()


# -- individual metric predicates -------------------------------------------
def test_is_progressive_requires_forward_progress():
    forward = Event(
        event_id="EVT-0001",
        match_id="MATCH-001",
        period=1,
        minute=10,
        second=0,
        team_id="HOME",
        player_id="HOME-04",
        event_type="pass",
        outcome="successful",
        start_x=40.0,
        start_y=50.0,
        end_x=65.0,
        end_y=50.0,
        possession_id="POS-0001",
        play_pattern="open_play",
    )
    backward = forward.model_copy(update={"end_x": 45.0, "start_x": 50.0})
    assert is_progressive(forward)
    assert not is_progressive(backward)


def test_is_final_third_entry_threshold():
    event = Event(
        event_id="EVT-0002",
        match_id="MATCH-001",
        period=1,
        minute=10,
        second=0,
        team_id="HOME",
        player_id="HOME-04",
        event_type="pass",
        outcome="successful",
        start_x=50.0,
        start_y=50.0,
        end_x=70.0,
        end_y=50.0,
        possession_id="POS-0002",
        play_pattern="open_play",
    )
    assert is_final_third_entry(event)
    outside = event.model_copy(update={"end_x": 60.0})
    assert not is_final_third_entry(outside)


def test_penalty_area_entry_requires_x_and_y(golden_models):
    for event in golden_models[:50]:
        if is_penalty_area_entry(event):
            assert event.end_x is not None and event.end_y is not None
            assert event.end_x >= 83.0


def test_recovery_predicate(golden_models):
    recoveries = [e for e in golden_models if is_recovery(e)]
    assert recoveries
    assert all(e.event_type == "possession_change" and e.outcome == "won" for e in recoveries)


def test_xg_proxy_is_bounded():
    close = Event(
        event_id="EVT-0003",
        match_id="MATCH-001",
        period=2,
        minute=60,
        second=0,
        team_id="HOME",
        player_id="HOME-09",
        event_type="shot",
        outcome="saved",
        start_x=95.0,
        start_y=50.0,
        end_x=100.0,
        end_y=50.0,
        possession_id="POS-0003",
        play_pattern="open_play",
    )
    far = close.model_copy(update={"start_x": 72.0, "start_y": 12.0})
    assert 0.0 <= xg_proxy(far) < xg_proxy(close) <= 1.0
