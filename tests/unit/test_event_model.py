"""Event schema and clock tests.

The clock regression test exists because a double-counted 45-minute offset once
pushed every second-half event past full time, silently emptying half the match.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.event import Event, match_clock_seconds


def make_event(**overrides) -> dict:
    base = {
        "event_id": "EVT-0203",
        "match_id": "MATCH-001",
        "period": 1,
        "minute": 58,
        "second": 24,
        "team_id": "HOME",
        "player_id": "HOME-07",
        "event_type": "pass",
        "outcome": "successful",
        "start_x": 51.2,
        "start_y": 38.1,
        "end_x": 73.4,
        "end_y": 41.7,
        "possession_id": "POS-0088",
        "play_pattern": "open_play",
    }
    base.update(overrides)
    return base


# -- clock -------------------------------------------------------------------
@pytest.mark.parametrize(
    ("period", "minute", "second", "expected"),
    [
        (1, 0, 0, 0),
        (1, 10, 0, 600),
        (1, 44, 59, 2699),
        (2, 45, 0, 2700),  # second-half kick-off
        (2, 60, 0, 3600),
        (2, 89, 59, 5399),
    ],
)
def test_match_clock_seconds(period, minute, second, expected):
    assert match_clock_seconds(period, minute, second) == expected


def test_second_half_never_exceeds_full_time():
    """Regression: half 2 must sit inside 2700-5400s, not beyond 5400s."""

    assert match_clock_seconds(2, 45, 0) == 2700
    assert match_clock_seconds(2, 89, 59) < 5400


def test_event_match_seconds_uses_global_clock():
    event = Event(**make_event(period=2, minute=45, second=0))
    assert event.match_seconds == 2700

    event = Event(**make_event(period=1, minute=45, second=0))
    assert event.match_seconds == 2700


# -- schema ------------------------------------------------------------------
def test_valid_pass_event_parses():
    event = Event(**make_event())
    assert event.team_matches_player


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"start_x": 120.0}, "coordinate out of range"),
        ({"start_x": -1.0}, "negative coordinate"),
        ({"second": 60}, "second out of range"),
        ({"minute": 200}, "minute out of range"),
        ({"player_id": "AWAY-07"}, "player from the other team"),
        ({"event_id": "BAD-1"}, "malformed event id"),
        ({"possession_id": "POS88"}, "malformed possession id"),
        ({"event_type": "carry"}, "unknown event type"),
        ({"play_pattern": "chaos"}, "unknown play pattern"),
        ({"outcome": "goal"}, "pass cannot produce a goal outcome"),
    ],
)
def test_invalid_events_are_rejected(overrides, reason):
    with pytest.raises(ValidationError):
        Event(**make_event(**overrides))


def test_pass_requires_end_coordinates():
    record = make_event(end_x=None, end_y=None)
    with pytest.raises(ValidationError):
        Event(**record)


def test_pressure_must_not_carry_end_coordinates():
    record = make_event(event_type="pressure", outcome="successful", end_x=70.0, end_y=40.0)
    with pytest.raises(ValidationError):
        Event(**record)


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        Event(**make_event(unexpected="x"))


def test_outcome_vocabulary_is_per_event_type():
    shot = Event(
        **make_event(
            event_type="shot",
            outcome="saved",
            end_x=100.0,
            end_y=50.0,
            start_x=88.0,
            start_y=47.0,
        )
    )
    assert shot.outcome == "saved"

    with pytest.raises(ValidationError):
        Event(
            **make_event(
                event_type="shot",
                outcome="successful",
                end_x=100.0,
                end_y=50.0,
            )
        )
