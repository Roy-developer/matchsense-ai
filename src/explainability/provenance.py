"""Provenance helpers: keep every published claim traceable to events."""

from __future__ import annotations

from src.models.event import Event
from src.models.insight import EvidenceBundle


def unresolved_event_ids(bundle: EvidenceBundle, events: list[Event]) -> list[str]:
    """Event ids cited by a bundle that do not exist in the match."""

    known = {e.event_id for e in events}
    return [event_id for event_id in bundle.observed.event_ids if event_id not in known]


def events_outside_window(bundle: EvidenceBundle, events: list[Event]) -> list[str]:
    """Cited events that fall outside the bundle's own window."""

    index = {e.event_id: e for e in events}
    outside: list[str] = []
    for event_id in bundle.observed.event_ids:
        event = index.get(event_id)
        if event is None:
            continue
        if not (
            bundle.window_start_second <= event.match_seconds < bundle.window_end_second
        ):
            outside.append(event_id)
    return outside


def provenance_chain(bundle: EvidenceBundle, events: list[Event]) -> list[dict]:
    """Event id -> minute/team/type for the Evidence Receipt UI."""

    index = {e.event_id: e for e in events}
    chain = []
    for event_id in bundle.observed.event_ids:
        event = index.get(event_id)
        if event is None:
            continue
        chain.append(
            {
                "event_id": event.event_id,
                "minute": event.minute,
                "second": event.second,
                "team_id": event.team_id,
                "player_id": event.player_id,
                "event_type": event.event_type,
                "outcome": event.outcome,
                "play_pattern": event.play_pattern,
            }
        )
    return chain


def is_bundle_grounded(bundle: EvidenceBundle, events: list[Event]) -> bool:
    return not unresolved_event_ids(bundle, events) and not events_outside_window(bundle, events)
