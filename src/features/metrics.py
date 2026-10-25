"""Configurable football feature calculations (F-003).

Every function here is a pure function of validated events. No randomness, no
I/O, no LLM. Numbers produced here are the only numbers the narrative layer is
ever allowed to mention.
"""

from __future__ import annotations

from src.models.event import Event

FINAL_THIRD_X = 66.0
PENALTY_AREA_X = 83.0
PENALTY_AREA_HALF_WIDTH = 20.16
PROGRESSIVE_PASS_X = 20.0


def is_final_third_entry(event: Event) -> bool:
    return event.event_type in {"pass", "shot"} and event.end_x is not None and event.end_x >= FINAL_THIRD_X


def is_penalty_area_entry(event: Event) -> bool:
    if event.end_x is None or event.end_y is None:
        return False
    return event.end_x >= PENALTY_AREA_X and abs(event.end_y - 50.0) <= PENALTY_AREA_HALF_WIDTH


def is_progressive(event: Event) -> bool:
    if event.event_type != "pass" or event.outcome != "successful" or event.end_x is None:
        return False
    return (event.end_x - event.start_x) >= PROGRESSIVE_PASS_X


def is_attacking_action(event: Event) -> bool:
    return event.event_type in {"pass", "shot"}


def is_recovery(event: Event) -> bool:
    return event.event_type == "possession_change" and event.outcome == "won"


def is_shot_on_target(event: Event) -> bool:
    return event.event_type == "shot" and event.outcome in {"goal", "saved"}


def xg_proxy(event: Event) -> float:
    """Documented heuristic shot-quality proxy - NOT a calibrated xG model."""

    if event.event_type != "shot" or event.end_x is None or event.end_y is None:
        return 0.0
    distance = ((100.0 - event.start_x) ** 2 + (50.0 - event.start_y) ** 2) ** 0.5
    closeness = max(0.02, 1.0 - distance / 60.0)
    angle = 1.0 - abs(event.start_y - 50.0) / 50.0
    return round(0.35 * closeness * (0.5 + 0.5 * angle), 4)


def xg_for_outcome(event: Event) -> float:
    """Credit only the quality actually realised (goal/saved/blocked/off target)."""

    if event.event_type != "shot":
        return 0.0
    quality = xg_proxy(event)
    if event.outcome == "goal":
        return 1.0
    if event.outcome == "saved":
        return quality
    if event.outcome == "blocked":
        return quality * 0.5
    return 0.0
