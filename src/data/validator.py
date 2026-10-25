"""Batch validation of a match file (kept separate from per-object validation)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.models.event import Event


class MatchValidationResult(BaseModel):
    model_config = {"extra": "forbid"}

    valid: bool
    event_count: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def validate_events(events: list[Event], *, tolerate_reordering: bool = False) -> MatchValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not events:
        return MatchValidationResult(valid=False, event_count=0, errors=["match has no events"])

    seen_ids: set[str] = set()
    seen_possession: dict[str, str] = {}
    matches = {e.match_id for e in events}
    if len(matches) > 1:
        errors.append(f"file mixes matches: {sorted(matches)}")

    previous_seconds = -1
    for event in events:
        if event.event_id in seen_ids:
            errors.append(f"duplicate event_id {event.event_id}")
        seen_ids.add(event.event_id)

        # possession continuity: an id must always belong to the same team
        owner = seen_possession.setdefault(event.possession_id, event.team_id)
        if owner != event.team_id:
            errors.append(
                f"possession {event.possession_id} changes team "
                f"({owner} -> {event.team_id}) at {event.event_id}"
            )

        if not tolerate_reordering and event.match_seconds < previous_seconds:
            errors.append(f"event {event.event_id} is out of chronological order")
        previous_seconds = max(previous_seconds, event.match_seconds)

    if len(events) < 60:
        warnings.append(
            f"only {len(events)} events: rolling windows will be sparse and the detector may stay silent"
        )

    return MatchValidationResult(
        valid=not errors, event_count=len(events), errors=errors, warnings=warnings
    )
