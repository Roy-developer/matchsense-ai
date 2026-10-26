"""Guardrails: what an interpretation is not allowed to say (AI-002).

The Critic Agent rejects unsupported context before anything reaches a viewer.
This module is the deterministic half of that judgement, so it is testable
without any model in the loop.
"""

from __future__ import annotations

import re

from src.models.insight import EvidenceBundle
from src.narrative.prompts import BLOCKED_PHRASES

NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
SIGNAL_COUNT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s+(?:independent\s+)?signals?\b")


class CritiqueResult:
    def __init__(self, decision: str, reasons: list[str]) -> None:
        self.decision = decision  # "accept" | "revise" | "reject"
        self.reasons = reasons

    def __bool__(self) -> bool:
        return self.decision != "reject"


def _numbers_in(text: str) -> list[float]:
    return [float(match) for match in NUMBER_PATTERN.findall(text)]


def _available_numbers(bundle: EvidenceBundle) -> set[float]:
    previous = bundle.derived.previous_metrics
    current = bundle.derived.current_metrics
    values: set[float] = set()
    for metrics in (previous, current):
        for field in metrics.model_dump().values():
            if isinstance(field, (int, float)):
                values.add(round(float(field), 4))
    for delta in bundle.derived.deltas.values():
        values.add(round(float(delta), 4))
    values.add(round(bundle.derived.confidence, 4))
    values.add(round(bundle.derived.control_score_change, 4))
    values.add(round(bundle.window_start_minute, 4))
    values.add(round(bundle.window_end_minute, 4))
    return values


def _is_supported(number: float, allowed: set[float], tolerance: float = 0.011) -> bool:
    """True when the number matches an evidence value or its percentage form.

    Prose rounds values, so comparison allows rounding at the precision the text
    used. Exact equality would reject every legitimate claim.
    """

    for candidate in allowed:
        if abs(number - candidate) <= tolerance:
            return True
        if abs(number - candidate * 100) <= tolerance:
            return True
        if abs(number / 100 - candidate) <= tolerance:
            return True
    return False


def critique(bundle: EvidenceBundle, claim: str, significance: str) -> CritiqueResult:
    text = f"{claim} {significance}".lower()
    reasons: list[str] = []

    for phrase in BLOCKED_PHRASES:
        if phrase in text:
            reasons.append(f"unsupported context: '{phrase}' is not in the event data")

    allowed = _available_numbers(bundle)
    grounded_signal_counts = {
        float(match.group(1))
        for match in SIGNAL_COUNT_PATTERN.finditer(text)
        if float(match.group(1)) == len(bundle.detector.triggered_signals)
    }
    for number in _numbers_in(text):
        if number not in grounded_signal_counts and not _is_supported(number, allowed):
            reasons.append(f"unsupported number: {number:g} does not appear in the evidence")

    if not bundle.detector.triggered_signals:
        reasons.append("no triggered signals, so no claim can be supported")

    if any(reason.startswith(("unsupported context", "unsupported number")) for reason in reasons):
        return CritiqueResult("reject", reasons)
    if reasons:
        return CritiqueResult("revise", reasons)
    return CritiqueResult("accept", [])
