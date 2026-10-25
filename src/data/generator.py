"""Deterministic synthetic match generator (F-002).

Rules this file must keep:
  * one seed -> one byte-identical match file;
  * sequences, not independent random rows;
  * fictional teams/players only (IP safety, Guide v2 section 16);
  * explicit, inspectable scenario injection so the demo always contains the
    situations the detector is meant to find.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from src.models.event import Event, MatchMeta

DEFAULT_SEED = 20261023
FINAL_THIRD_X = 66.0
PENALTY_AREA_X = 83.0
PROGRESSIVE_THRESHOLD = 20.0

HOME_TEAM = "Harbour Rovers"
AWAY_TEAM = "Ridgeway Athletic"


@dataclass
class Player:
    player_id: str
    role: str


@dataclass
class Scenario:
    """A scripted passage of play the demo needs to contain."""

    name: str
    start_minute: int
    end_minute: int
    team_id: str
    kind: str  # "control" | "counter" | "breakdown" | "hero"
    intensity: float = 1.0
    period: int = 1


# Scenarios are declarative data, so the golden match is auditable.
# (name, from, to, team, kind, intensity, period)
GOLDEN_SCENARIOS: list[Scenario] = [
    Scenario("calm_opening", 1, 20, "HOME", "control", 0.45, 1),
    Scenario("away_spell", 26, 40, "AWAY", "control", 0.9, 1),
    Scenario("counter_home_1", 47, 49, "HOME", "counter", 1.0, 2),
    Scenario("hero_sequence", 52, 56, "HOME", "hero", 1.0, 2),
    Scenario("home_control_shift", 55, 68, "HOME", "control", 1.35, 2),
    Scenario("counter_home_2", 70, 72, "HOME", "counter", 1.0, 2),
    Scenario("away_breakdown", 74, 79, "AWAY", "breakdown", 1.2, 2),
    Scenario("home_control_shift_2", 81, 88, "HOME", "control", 1.15, 2),
]


@dataclass
class MatchBuilder:
    seed: int = DEFAULT_SEED
    match_id: str = "MATCH-001"
    scenarios: list[Scenario] = field(default_factory=lambda: list(GOLDEN_SCENARIOS))

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        self.events: list[dict] = []
        self.event_counter = 0
        self.possession_counter = 0
        self.possession_id = self._new_possession()
        self.home_goals = 0
        self.away_goals = 0
        self.players = {
            "HOME": [Player(f"HOME-{i:02d}", role) for i, role in enumerate(["gk"] + ["out"] * 10, 1)],
            "AWAY": [Player(f"AWAY-{i:02d}", role) for i, role in enumerate(["gk"] + ["out"] * 10, 1)],
        }

    # -- identifiers ---------------------------------------------------------
    def _new_possession(self) -> str:
        self.possession_counter += 1
        return f"POS-{self.possession_counter:04d}"

    def _next_event_id(self) -> str:
        self.event_counter += 1
        return f"EVT-{self.event_counter:04d}"

    # -- helpers -------------------------------------------------------------
    def _scenario_for(self, minute: int) -> tuple[Scenario, float]:
        """Return the active scenario and its influence on possession share."""

        active = [s for s in self.scenarios if s.start_minute <= minute <= s.end_minute]
        if not active:
            return Scenario("neutral", minute, minute, "NEUTRAL", "control", 0.0), 0.5
        scenario = active[-1]
        influence = scenario.intensity
        if scenario.team_id == "NEUTRAL":
            return scenario, 0.5
        return scenario, 0.5 + 0.15 * influence * (1 if scenario.team_id == "HOME" else -1)

    def _outfield(self, team: str, rng: random.Random) -> str:
        return rng.choice(self.players[team][1:]).player_id

    def _emit(
        self,
        *,
        team_id: str,
        player_id: str,
        event_type: str,
        outcome: str,
        minute: int,
        second: int,
        start: tuple[float, float],
        end: tuple[float, float] | None,
        play_pattern: str,
        possession_id: str | None = None,
        period: int = 1,
    ) -> None:
        record = {
            "event_id": self._next_event_id(),
            "match_id": self.match_id,
            "period": period,
            "minute": minute,
            "second": second,
            "team_id": team_id,
            "player_id": player_id,
            "event_type": event_type,
            "outcome": outcome,
            "start_x": round(start[0], 1),
            "start_y": round(start[1], 1),
            "end_x": round(end[0], 1) if end else None,
            "end_y": round(end[1], 1) if end else None,
            "possession_id": possession_id or self.possession_id,
            "play_pattern": play_pattern,
        }
        # Fail fast: nothing invalid ever reaches the file.
        Event(**record)
        self.events.append(record)

    def _safe_xy(self, rng: random.Random, lo: float = 15.0, hi: float = 75.0) -> tuple[float, float]:
        return rng.uniform(lo, hi), rng.uniform(10.0, 90.0)

    # -- passages ------------------------------------------------------------
    def _build_chain(
        self,
        team: str,
        minute: int,
        rng: random.Random,
        *,
        period: int = 1,
        intensity: float = 1.0,
        max_length: int | None = None,
        pattern: str = "open_play",
        start_pos: tuple[float, float] | None = None,
    ) -> None:
        """A possession chain: progressive passes, optional pressure, maybe a shot."""

        self.possession_id = self._new_possession()
        second = rng.randint(0, 55)
        x, y = start_pos or self._safe_xy(rng, 20.0, 55.0)
        length = max_length or max(2, int(round(rng.uniform(2, 5) * intensity)))
        opponent = "AWAY" if team == "HOME" else "HOME"

        for _ in range(length):
            second = min(59, second + rng.randint(3, 12))
            player = self._outfield(team, rng)
            forward = rng.uniform(8.0, 24.0) * (1.0 + 0.25 * (intensity - 1.0))
            end_x = min(99.0, x + forward)
            end_y = min(95.0, max(5.0, y + rng.uniform(-16.0, 16.0)))
            success = rng.random() < (0.72 + 0.1 * (intensity - 1.0))
            self._emit(
                team_id=team,
                player_id=player,
                event_type="pass",
                outcome="successful" if success else "unsuccessful",
                minute=minute,
                second=second,
                start=(x, y),
                end=(end_x, end_y),
                play_pattern=pattern,
                possession_id=self.possession_id,
                period=period,
            )
            if not success:
                # loose ball -> opponent recovery ends the chain (new possession)
                self.possession_id = self._new_possession()
                self._emit(
                    team_id=opponent,
                    player_id=self._outfield(opponent, rng),
                    event_type="possession_change",
                    outcome="won",
                    minute=minute,
                    second=min(59, second + 2),
                    start=(end_x, end_y),
                    end=None,
                    play_pattern="transition",
                    possession_id=self.possession_id,
                    period=period,
                )
                self.possession_id = self._new_possession()
                return
            if rng.random() < 0.45:
                self._emit(
                    team_id=team,
                    player_id=player,
                    event_type="pressure",
                    outcome="successful",
                    minute=minute,
                    second=min(59, second + 1),
                    start=(end_x, end_y),
                    end=None,
                    play_pattern=pattern,
                    possession_id=self.possession_id,
                    period=period,
                )
            x, y = end_x, end_y

        if x >= 78.0 and rng.random() < 0.35 * intensity:
            self._build_shot(
                team, minute, min(59, second + 6), rng, pattern=pattern, period=period
            )

    def _build_shot(
        self,
        team: str,
        minute: int,
        second: int,
        rng: random.Random,
        *,
        pattern: str = "open_play",
        period: int = 1,
    ) -> None:
        player = self._outfield(team, rng)
        roll = rng.random()
        if roll < 0.24:
            outcome = "goal"
        elif roll < 0.55:
            outcome = "saved"
        elif roll < 0.75:
            outcome = "blocked"
        else:
            outcome = "off_target"
        self._emit(
            team_id=team,
            player_id=player,
            event_type="shot",
            outcome=outcome,
            minute=minute,
            second=second,
            start=(rng.uniform(78.0, 92.0), rng.uniform(35.0, 65.0)),
            end=(100.0, 50.0),
            play_pattern=pattern,
            possession_id=self.possession_id,
            period=period,
        )
        if outcome == "goal":
            if team == "HOME":
                self.home_goals += 1
            else:
                self.away_goals += 1
            self.possession_id = self._new_possession()

    def _build_counter(self, team: str, minute: int, *, period: int = 2) -> None:
        """Fast, direct transition: short chain at speed, then a shot."""

        rng = self.rng
        self._build_chain(
            team,
            minute,
            rng,
            period=period,
            intensity=1.4,
            max_length=3,
            pattern="counterattack",
            start_pos=(rng.uniform(20.0, 32.0), rng.uniform(30.0, 70.0)),
        )
        if rng.random() < 0.5:
            self._build_shot(
                team, minute, rng.randint(40, 58), rng, pattern="counterattack", period=period
            )

    def _build_defensive_breakdown(self, team: str, minute: int, *, period: int = 2) -> None:
        """Team loses the ball cheaply in its own third and concedes pressure."""

        rng = self.rng
        opponent = "AWAY" if team == "HOME" else "HOME"
        self.possession_id = self._new_possession()
        for _ in range(2):
            second = rng.randint(5, 50)
            self._emit(
                team_id=team,
                player_id=self._outfield(team, rng),
                event_type="pass",
                outcome="unsuccessful",
                minute=minute,
                second=second,
                start=(rng.uniform(12.0, 28.0), rng.uniform(20.0, 80.0)),
                end=(rng.uniform(35.0, 50.0), rng.uniform(20.0, 80.0)),
                play_pattern="open_play",
                possession_id=self.possession_id,
                period=period,
            )
            self.possession_id = self._new_possession()
            self._emit(
                team_id=opponent,
                player_id=self._outfield(opponent, rng),
                event_type="possession_change",
                outcome="won",
                minute=minute,
                second=min(59, second + 2),
                start=(rng.uniform(35.0, 50.0), rng.uniform(20.0, 80.0)),
                end=None,
                play_pattern="transition",
                possession_id=self.possession_id,
                period=period,
            )
            self.possession_id = self._new_possession()
        self._build_chain(
            opponent,
            minute,
            rng,
            period=period,
            intensity=1.3,
            max_length=4,
            start_pos=(rng.uniform(50.0, 62.0), rng.uniform(30.0, 70.0)),
        )

    # -- assembly ------------------------------------------------------------
    def build(self) -> list[dict]:
        """Emit a full 90-minute match.

        Minute-by-minute attacks alternate between the teams so possession swings
        are visible at 5-minute resolution; scripted scenarios then tilt it
        deliberately. Both halves use broadcast event clocks (period 1: 0-45,
        period 2: 45-90), which is what the validator and window engine expect.
        """

        covered: set[int] = set()
        for scenario in self.scenarios:
            covered.update(range(scenario.start_minute, scenario.end_minute + 1))

        for minute in range(1, 90):
            if minute in covered:
                continue
            period = 1 if minute < 45 else 2
            team = "HOME" if minute % 2 == 1 else "AWAY"
            self._build_attack(team, minute, period=period, intensity=0.85)

        for scenario in self.scenarios:
            if scenario.kind == "control":
                for minute in range(scenario.start_minute, scenario.end_minute + 1):
                    self._build_attack(
                        scenario.team_id,
                        minute,
                        period=scenario.period,
                        intensity=scenario.intensity,
                    )
            elif scenario.kind == "counter":
                for minute in range(scenario.start_minute, scenario.end_minute + 1, 2):
                    self._build_counter(scenario.team_id, minute, period=scenario.period)
            elif scenario.kind == "breakdown":
                for minute in range(scenario.start_minute, scenario.end_minute + 1, 2):
                    self._build_defensive_breakdown(
                        scenario.team_id, minute, period=scenario.period
                    )
            elif scenario.kind == "hero":
                for minute in range(scenario.start_minute, scenario.end_minute + 1):
                    self._build_hero_minute(
                        scenario.team_id, minute, period=scenario.period
                    )

        self._normalise_ids()
        return self.events

    def _build_attack(self, team: str, minute: int, *, period: int, intensity: float) -> None:
        """One team's attacking minute; the opponent keeps the ball meanwhile."""

        self._build_chain(team, minute, self.rng, period=period, intensity=intensity)
        self._build_keeping("AWAY" if team == "HOME" else "HOME", minute, period=period)

    def _build_keeping(self, team: str, minute: int, *, period: int) -> None:
        """Quiet out-of-possession retention, so possession share stays near
        50/50 outside the scripted scenarios."""

        rng = self.rng
        self.possession_id = self._new_possession()
        for _ in range(2):
            y = rng.uniform(15.0, 85.0)
            self._emit(
                team_id=team,
                player_id=self._outfield(team, rng),
                event_type="pass",
                outcome="successful",
                minute=minute,
                second=rng.randint(4, 55),
                start=(rng.uniform(30.0, 55.0), y),
                end=(rng.uniform(40.0, 62.0), y),
                play_pattern="open_play",
                possession_id=self.possession_id,
                period=period,
            )

    def _build_hero_minute(self, team: str, minute: int, *, period: int) -> None:
        """One minute of a player-led attacking sequence."""

        self._build_chain(
            team,
            minute,
            self.rng,
            period=period,
            intensity=1.2,
            max_length=4,
            start_pos=(self.rng.uniform(35.0, 55.0), self.rng.uniform(35.0, 65.0)),
        )

    def _normalise_ids(self) -> None:
        """Sort chronologically and renumber event ids to match the clock.

        Passages are generated per minute rather than strictly in time order, so
        the id sequence is rebuilt once, in place, before build() returns.
        """

        self.events.sort(
            key=lambda e: (e["period"], e["minute"], e["second"], e["possession_id"])
        )
        for index, event in enumerate(self.events, start=1):
            event["event_id"] = f"EVT-{index:04d}"

    def meta(self) -> MatchMeta:
        return MatchMeta(
            match_id=self.match_id,
            home_team=HOME_TEAM,
            away_team=AWAY_TEAM,
            seed=self.seed,
            event_count=len(self.events),
            home_goals=self.home_goals,
            away_goals=self.away_goals,
            penalty_area_x=PENALTY_AREA_X,
            final_third_x=FINAL_THIRD_X,
            scenario_markers=[f"{s.kind}:{s.team_id}:{s.start_minute}-{s.end_minute}" for s in self.scenarios],
        )


def build_match(seed: int = DEFAULT_SEED, match_id: str = "MATCH-001") -> tuple[list[dict], MatchMeta]:
    builder = MatchBuilder(seed=seed, match_id=match_id)
    events = builder.build()
    return events, builder.meta()


def write_match(
    out_dir: str | Path,
    seed: int = DEFAULT_SEED,
    match_id: str = "MATCH-001",
) -> tuple[Path, Path]:
    """Write match_XXX.jsonl + match_XXX.meta.json. Deterministic for a given seed."""

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    events, meta = build_match(seed=seed, match_id=match_id)

    jsonl_path = out / f"{match_id.lower().replace('-', '_')}.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as fh:
        for event in events:
            fh.write(json.dumps(event, sort_keys=True) + "\n")

    meta_path = out / f"{match_id.lower().replace('-', '_')}.meta.json"
    meta_path.write_text(
        json.dumps(meta.model_dump(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return jsonl_path, meta_path
