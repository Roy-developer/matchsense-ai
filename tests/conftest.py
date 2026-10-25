"""Shared test fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.generator import build_match  # noqa: E402
from src.models.event import Event  # noqa: E402


@pytest.fixture(scope="session")
def golden_events() -> list[dict]:
    events, _ = build_match()
    return events


@pytest.fixture(scope="session")
def golden_models(golden_events) -> list[Event]:
    return [Event(**record) for record in golden_events]
