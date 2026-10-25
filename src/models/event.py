"""Canonical event model (Guide v2 section 5, impl2 Phase 2).

One Pydantic schema is the contract for the generator, the loader, the replay
engine and the analytics layer. Nothing downstream may accept an unvalidated
event.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

EventType = Literal["pass", "shot", "tackle", "possession_change", "pressure", "foul"]

Outcome = Literal[
    "successful",
    "unsuccessful",
    "goal",
    "saved",
    "blocked",
    "off_target",
    "won",
    "lost",
]

PLAY_PATTERNS = ("open_play", "counterattack", "set_piece", "transition", "press")

TEAMS = ("HOME", "AWAY")


class Event(BaseModel):
    """A single football event on a 100x100 normalized pitch.

    Coordinates use pitch-absolute values: both teams attack towards x=100, so
    the analytics layer never needs to flip coordinates.
    """

    model_config = {"extra": "forbid", "frozen": True}

    event_id: str = Field(pattern=r"^EVT-\d{4,}$")
    match_id: str = Field(min_length=1)
    period: int = Field(ge=1, le=5)
    minute: int = Field(ge=0, le=120)
    second: int = Field(ge=0, le=59)
    team_id: Literal["HOME", "AWAY"]
    player_id: str = Field(pattern=r"^(HOME|AWAY)-\d{2}$")
    event_type: EventType
    outcome: Outcome
    start_x: float = Field(ge=0, le=100)
    start_y: float = Field(ge=0, le=100)
    end_x: float | None = Field(default=None, ge=0, le=100)
    end_y: float | None = Field(default=None, ge=0, le=100)
    possession_id: str = Field(pattern=r"^POS-\d{4,}$")
    play_pattern: Literal["open_play", "counterattack", "set_piece", "transition", "press"]

    # ---- derived convenience -------------------------------------------------
    @property
    def match_seconds(self) -> int:
        """Monotonic simulated seconds from kick-off.

        Period 2 is event-clocked from 45', so the second half starts at 2700s.
        """

        return match_clock_seconds(self.period, self.minute, self.second)

    @property
    def team_matches_player(self) -> bool:
        return self.player_id.split("-")[0] == self.team_id

    # ---- validation ----------------------------------------------------------
    @field_validator("player_id")
    @classmethod
    def _player_team_prefix(cls, v: str) -> str:
        prefix = v.split("-")[0]
        if prefix not in TEAMS:
            raise ValueError(f"player_id {v!r} must start with HOME- or AWAY-")
        return v

    @model_validator(mode="after")
    def _coherence(self) -> "Event":
        if not self.team_matches_player:
            raise ValueError(
                f"player {self.player_id} cannot act for team {self.team_id}"
            )

        # events that move the ball need an end location
        needs_end = self.event_type in {"pass", "shot"}
        has_end = self.end_x is not None and self.end_y is not None
        if needs_end and not has_end:
            raise ValueError(f"{self.event_type} event {self.event_id} requires end_x/end_y")
        if not needs_end and has_end:
            raise ValueError(
                f"{self.event_type} event {self.event_id} must not carry end coordinates"
            )

        # outcome vocabulary depends on the event type
        if self.event_type == "pass" and self.outcome not in {"successful", "unsuccessful"}:
            raise ValueError(f"pass event {self.event_id} has invalid outcome {self.outcome!r}")
        if self.event_type == "shot" and self.outcome not in {
            "goal",
            "saved",
            "blocked",
            "off_target",
        }:
            raise ValueError(f"shot event {self.event_id} has invalid outcome {self.outcome!r}")
        if self.event_type in {"tackle", "pressure", "foul"} and self.outcome not in {
            "successful",
            "unsuccessful",
            "won",
            "lost",
        }:
            raise ValueError(
                f"{self.event_type} event {self.event_id} has invalid outcome {self.outcome!r}"
            )
        if self.event_type == "possession_change" and self.outcome not in {
            "won",
            "lost",
        }:
            raise ValueError(
                f"possession_change event {self.event_id} has invalid outcome {self.outcome!r}"
            )
        return self


class MatchMeta(BaseModel):
    """Side-car metadata for a generated match file."""

    model_config = {"extra": "forbid"}

    match_id: str
    home_team: str
    away_team: str
    competition: str = "Synthetic Friendly"
    seed: int
    data_version: str = "synthetic-demo-v1"
    event_count: int
    home_goals: int
    away_goals: int
    penalty_area_x: float = 83.0
    final_third_x: float = 66.0
    stages_completed: int = 5
    scenario_markers: list[str] = Field(default_factory=list)


def match_clock_seconds(period: int, minute: int, second: int) -> int:
    """Simulated seconds from kick-off for an event-clock (period, minute, second).

    Broadcast event data uses a match-global minute field: period 1 runs 0-45 and
    period 2 runs 45-90. Because `minute` already carries the elapsed match time,
    NO offset may be added - doing so double-counts the 45 minutes that separate
    the halves.

      period 1, 44' -> 2640s      period 2, 45' -> 2700s (second-half kick-off)
      period 2, 60' -> 3600s      period 2, 89' -> 5340s
    """

    return minute * 60 + second
