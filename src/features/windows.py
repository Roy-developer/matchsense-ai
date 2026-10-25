"""Rolling-window feature engineering (Guide v2 section 6).

Compares the current 300 simulated seconds with the immediately preceding 300
seconds and exposes provenance for every number it returns.
"""

from __future__ import annotations

from src.features.metrics import (
    is_attacking_action,
    is_final_third_entry,
    is_penalty_area_entry,
    is_progressive,
    is_recovery,
    is_shot_on_target,
    xg_for_outcome,
)
from src.models.event import Event
from src.models.insight import WindowComparison, WindowMetrics

WINDOW_SECONDS = 300
# Regular time is 0-5400s, but stoppage time legitimately runs past 90'.
# MAX_MATCH_SECONDS only guards the pathological case.
MATCH_LENGTH_SECONDS = 90 * 60
MAX_MATCH_SECONDS = 100 * 60


def window_bounds(window_end_second: int) -> tuple[int, int]:
    """Inclusive start, exclusive end."""

    end = min(window_end_second, MAX_MATCH_SECONDS)
    return max(0, end - WINDOW_SECONDS), end


def _events_in(events: list[Event], start: int, end: int, team_id: str) -> list[Event]:
    return [e for e in events if start <= e.match_seconds < end and e.team_id == team_id]


def compute_window(
    events: list[Event], window_end_second: int, team_id: str
) -> WindowMetrics:
    start, end = window_bounds(window_end_second)
    team_events = _events_in(events, start, end, team_id)
    opponent = "AWAY" if team_id == "HOME" else "HOME"
    opponent_events = _events_in(events, start, end, opponent)
    all_events = _events_in(events, start, end, team_id) + opponent_events

    passes_attempted = sum(1 for e in team_events if e.event_type == "pass")
    passes_completed = sum(1 for e in team_events if e.event_type == "pass" and e.outcome == "successful")
    shots = [e for e in team_events if e.event_type == "shot"]

    possession_share = (
        len(team_events) / len(all_events) if all_events else 0.0
    )
    completion = (passes_completed / passes_attempted) if passes_attempted else 0.0

    sequences = _sequence_lengths(team_events)

    return WindowMetrics(
        start_second=start,
        end_second=end,
        start_minute=round(start / 60.0, 2),
        end_minute=round(end / 60.0, 2),
        event_count=len(all_events),
        passes_attempted=passes_attempted,
        passes_completed=passes_completed,
        progressive_passes=sum(1 for e in team_events if is_progressive(e)),
        final_third_entries=sum(1 for e in team_events if is_final_third_entry(e)),
        penalty_area_entries=sum(1 for e in team_events if is_penalty_area_entry(e)),
        shots=len(shots),
        shots_on_target=sum(1 for e in shots if is_shot_on_target(e)),
        goals=sum(1 for e in shots if e.outcome == "goal"),
        recoveries=sum(1 for e in team_events if is_recovery(e)),
        presses=sum(1 for e in team_events if e.event_type == "pressure"),
        attacking_actions=sum(1 for e in team_events if is_attacking_action(e)),
        counterattack_actions=sum(1 for e in team_events if e.play_pattern == "counterattack"),
        threat_added=round(sum(xg_for_outcome(e) for e in shots), 4),
        possession_share=round(possession_share, 4),
        pass_completion_pct=round(completion * 100, 2),
        control_score=0.0,  # filled by compare_windows, which has both sides
        average_sequence_length=round(sum(sequences) / len(sequences), 2) if sequences else 0.0,
        supporting_event_ids=[e.event_id for e in team_events],
    )


def _sequence_lengths(team_events: list[Event]) -> list[int]:
    """Length of each uninterrupted, same-team, same-possession run of actions."""

    lengths: list[int] = []
    current_key: tuple[str, str] | None = None
    current_len = 0
    for event in team_events:
        if event.event_type not in {"pass", "shot"}:
            continue
        key = (event.team_id, event.possession_id)
        if key == current_key:
            current_len += 1
        else:
            if current_len:
                lengths.append(current_len)
            current_key, current_len = key, 1
    if current_len:
        lengths.append(current_len)
    return lengths


def control_score(window: WindowMetrics, *, team_id: str, opponent_window: WindowMetrics) -> float:
    """Weighted heuristic control score in [0, 1] - a design choice, not a fact."""

    possession = window.possession_share
    progressive = min(1.0, window.progressive_passes / 6.0)
    final_third = min(1.0, window.final_third_entries / 8.0)
    shots = min(1.0, window.shots / 3.0)
    threat = min(1.0, window.threat_added / 0.6)
    recoveries = min(1.0, window.recoveries / 4.0)

    score = (
        0.20 * possession
        + 0.15 * progressive
        + 0.20 * final_third
        + 0.15 * shots
        + 0.15 * threat
        + 0.15 * recoveries
    )
    return round(min(1.0, max(0.0, score)), 4)


def compare_windows(
    events: list[Event], window_end_second: int, team_id: str
) -> WindowComparison:
    opponent = "AWAY" if team_id == "HOME" else "HOME"
    start, end = window_bounds(window_end_second)
    previous_end = start

    previous = compute_window(events, previous_end, team_id)
    current = compute_window(events, end, team_id)
    previous_opp = compute_window(events, previous_end, opponent)
    current_opp = compute_window(events, end, opponent)

    previous.control_score = control_score(previous, team_id=team_id, opponent_window=previous_opp)
    current.control_score = control_score(current, team_id=team_id, opponent_window=current_opp)

    return WindowComparison(
        team_id=team_id,  # type: ignore[arg-type]
        previous=previous,
        current=current,
        possession_share_delta=round(current.possession_share - previous.possession_share, 4),
        progressive_passes_delta=current.progressive_passes - previous.progressive_passes,
        final_third_entries_delta=current.final_third_entries - previous.final_third_entries,
        shots_delta=current.shots - previous.shots,
        threat_added_delta=round(current.threat_added - previous.threat_added, 4),
        recoveries_delta=current.recoveries - previous.recoveries,
        presses_delta=current.presses - previous.presses,
        attacking_actions_delta=current.attacking_actions - previous.attacking_actions,
        control_score_delta=round(current.control_score - previous.control_score, 4),
        pass_completion_delta=round(current.pass_completion_pct - previous.pass_completion_pct, 2),
    )


def timeline_endpoints(events: list[Event], step_seconds: int = WINDOW_SECONDS) -> list[int]:
    """Window end-points from the first full window to the end of the match."""

    if not events:
        return []
    last = min(MAX_MATCH_SECONDS, max(e.match_seconds for e in events))
    endpoints = list(range(WINDOW_SECONDS, last + 1, step_seconds))
    return endpoints or [last]
