"""Generator determinism, realism and scenario-injection tests (F-002)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data.generator import DEFAULT_SEED, build_match, write_match
from src.data.loader import load_match
from src.data.validator import validate_events
from src.models.event import Event


def test_same_seed_produces_identical_events():
    first, meta_a = build_match(DEFAULT_SEED)
    second, meta_b = build_match(DEFAULT_SEED)
    assert first == second
    assert meta_a.model_dump() == meta_b.model_dump()


def test_different_seed_produces_different_events():
    first, _ = build_match(DEFAULT_SEED)
    second, _ = build_match(DEFAULT_SEED + 1)
    assert first != second


def test_generated_match_is_valid(golden_events):
    events = [Event(**record) for record in golden_events]
    result = validate_events(events)
    assert result.valid, result.errors


def test_event_ids_are_unique_and_ordered(golden_events):
    ids = [e["event_id"] for e in golden_events]
    assert len(ids) == len(set(ids))
    assert ids == [f"EVT-{i:04d}" for i in range(1, len(ids) + 1)]


def test_match_covers_both_halves(golden_events):
    events = [Event(**record) for record in golden_events]
    assert {e.period for e in events} == {1, 2}

    last_first_half = max(e.match_seconds for e in events if e.period == 1)
    first_second_half = min(e.match_seconds for e in events if e.period == 2)

    assert last_first_half <= 2700
    assert first_second_half >= 2700
    # every 5-minute window of the match must contain events
    for start in range(0, 5400, 300):
        in_window = [e for e in events if start <= e.match_seconds < start + 300]
        assert in_window, f"window {start // 60}-{(start + 300) // 60} is empty"


def test_scoreline_is_believable(golden_events):
    events = [Event(**record) for record in golden_events]
    goals = [e for e in events if e.event_type == "shot" and e.outcome == "goal"]
    assert 1 <= len(goals) <= 8, f"unrealistic scoreline: {len(goals)} goals"

    shots = [e for e in events if e.event_type == "shot"]
    assert 6 <= len(shots) <= 40, f"unrealistic shot count: {len(shots)}"


def test_demo_scenarios_are_present(golden_events):
    """The detector can only find what the generator actually injects."""

    events = [Event(**record) for record in golden_events]
    window = [e for e in events if 55 * 60 <= e.match_seconds < 68 * 60 and e.team_id == "HOME"]
    assert len(window) >= 40, "home pressure spell 55-68 is too thin"

    counters = [e for e in events if e.play_pattern == "counterattack"]
    assert len(counters) >= 4, "counterattack scenarios missing"

    # both halves contain a home attacking surge
    second_half_home = [e for e in events if e.period == 2 and e.team_id == "HOME"]
    assert len(second_half_home) > 60


def test_write_match_is_byte_identical(tmp_path: Path):
    first_dir = tmp_path / "a"
    second_dir = tmp_path / "b"
    write_match(first_dir, seed=DEFAULT_SEED)
    write_match(second_dir, seed=DEFAULT_SEED)

    a = (first_dir / "match_001.jsonl").read_bytes()
    b = (second_dir / "match_001.jsonl").read_bytes()
    assert a == b


def test_metadata_matches_file(tmp_path: Path):
    write_match(tmp_path, seed=DEFAULT_SEED)
    events, meta, result = load_match(tmp_path)

    assert result.valid
    assert meta.event_count == len(events)
    goals = [e for e in events if e.event_type == "shot" and e.outcome == "goal"]
    assert meta.home_goals == sum(1 for e in goals if e.team_id == "HOME")
    assert meta.away_goals == sum(1 for e in goals if e.team_id == "AWAY")


def test_metadata_is_valid_json(tmp_path: Path):
    write_match(tmp_path, seed=DEFAULT_SEED)
    payload = json.loads((tmp_path / "match_001.meta.json").read_text(encoding="utf-8"))
    assert payload["match_id"] == "MATCH-001"
    assert payload["seed"] == DEFAULT_SEED


def test_validation_rejects_duplicate_ids(golden_events):
    events = [Event(**record) for record in golden_events[:20]]
    duplicated = events + [events[0]]
    result = validate_events(duplicated, tolerate_reordering=True)
    assert not result.valid
    assert any("duplicate event_id" in error for error in result.errors)


def test_validation_rejects_out_of_order_events(golden_events):
    events = [Event(**record) for record in golden_events[:20]]
    shuffled = [events[5], events[1], *events[2:5], events[0], *events[6:]]
    result = validate_events(shuffled)
    assert not result.valid


def test_validation_warns_on_sparse_match(golden_events):
    events = [Event(**record) for record in golden_events[:10]]
    result = validate_events(events)
    assert result.warnings


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_generation_is_valid_for_arbitrary_seeds(seed):
    events, _ = build_match(seed)
    result = validate_events([Event(**record) for record in events])
    assert result.valid, result.errors
