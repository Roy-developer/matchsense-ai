"""Charts for the dashboard (kept separate so the app file stays readable)."""

from __future__ import annotations

import pandas as pd

from src.features.windows import timeline_endpoints, compare_windows
from src.models.event import Event


def control_timeline(events: list[Event], step: int = 300) -> pd.DataFrame:
    """Control score per team per window end-point."""

    rows = []
    for end in timeline_endpoints(events, step_seconds=step):
        row = {"minute": end // 60}
        for team in ("HOME", "AWAY"):
            comparison = compare_windows(events, end, team)
            row[team] = comparison.current.control_score
        rows.append(row)
    return pd.DataFrame(rows)


def event_volume(events: list[Event], step: int = 300) -> pd.DataFrame:
    rows = []
    for end in timeline_endpoints(events, step_seconds=step):
        start = max(0, end - step)
        window = [e for e in events if start <= e.match_seconds < end]
        rows.append(
            {
                "minute": end // 60,
                "HOME": sum(1 for e in window if e.team_id == "HOME"),
                "AWAY": sum(1 for e in window if e.team_id == "AWAY"),
            }
        )
    return pd.DataFrame(rows)
