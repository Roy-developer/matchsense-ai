"""Loading matches from disk (JSONL + side-car metadata)."""

from __future__ import annotations

import json
from pathlib import Path

from src.data.validator import MatchValidationResult, validate_events
from src.models.event import Event, MatchMeta

DEFAULT_MATCH_ID = "MATCH-001"


def _paths(data_dir: str | Path, match_id: str) -> tuple[Path, Path]:
    stem = match_id.lower().replace("-", "_")
    base = Path(data_dir)
    return base / f"{stem}.jsonl", base / f"{stem}.meta.json"


def load_events(path: str | Path) -> list[Event]:
    events: list[Event] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(Event(**json.loads(line)))
            except Exception as exc:  # noqa: BLE001 - message includes line number
                raise ValueError(f"{path}:{lineno}: invalid event: {exc}") from exc
    return events


def load_match(
    data_dir: str | Path, match_id: str = DEFAULT_MATCH_ID
) -> tuple[list[Event], MatchMeta, MatchValidationResult]:
    jsonl_path, meta_path = _paths(data_dir, match_id)
    if not jsonl_path.exists():
        raise FileNotFoundError(
            f"{jsonl_path} not found. Run: python -m scripts.generate_match"
        )
    events = load_events(jsonl_path)
    result = validate_events(events)
    meta = (
        MatchMeta(**json.loads(meta_path.read_text(encoding="utf-8")))
        if meta_path.exists()
        else MatchMeta(
            match_id=match_id,
            home_team="Home",
            away_team="Away",
            seed=0,
            event_count=len(events),
            home_goals=sum(1 for e in events if e.event_type == "shot" and e.outcome == "goal" and e.team_id == "HOME"),
            away_goals=sum(1 for e in events if e.event_type == "shot" and e.outcome == "goal" and e.team_id == "AWAY"),
        )
    )
    return events, meta, result
