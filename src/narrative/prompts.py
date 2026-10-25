"""Canonical claim vocabulary and prompt material (AI layer).

Anything not derivable from these facts is blocked by verification, so the
allowed vocabulary is deliberately narrow.
"""

from __future__ import annotations

from src.models.insight import EvidenceBundle

# Words an interpretation may use. Anything else is treated as an unsupported
# claim (formation, fatigue, tactics, invented statistics) and rejected.
ALLOWED_FOOTBALL_TERMS = {
    "possession",
    "pressure",
    "control",
    "shots",
    "shot",
    "passes",
    "passing",
    "final third",
    "progressive",
    "recoveries",
    "recovery",
    "turnovers",
    "attacks",
    "attacking",
    "counter",
    "counterattack",
    "momentum",
    "sustained",
    "windows",
    "window",
    "minutes",
    "minute",
    "spell",
    "period",
    "surge",
    "sequence",
    "threat",
    "entries",
}

# Phrases that require information the event data does not contain.
BLOCKED_PHRASES = (
    "formation",
    "4-4-2",
    "4-3-3",
    "3-5-2",
    "5-3-2",
    "fatigue",
    "tired",
    "injured",
    "injury",
    "tactical instruction",
    "manager told",
    "coach told",
    "xG of",
    "league table",
    "premier league",
    "points",
    "possession was 6",
)

SIGNAL_PHRASES = {
    "possession_share": "share of possession",
    "progressive_passes": "progressive passes",
    "final_third_entries": "final-third entries",
    "shots": "shots",
    "threat": "shot threat",
    "recoveries": "recoveries",
}


def describe_signals(bundle: EvidenceBundle) -> list[str]:
    """Human-readable list of the triggered signals, in detector order."""

    phrases = []
    for signal in bundle.detector.triggered_signals:
        label = SIGNAL_PHRASES.get(signal.name, signal.name)
        phrases.append(f"{label} rising from {signal.previous_value:g} to {signal.current_value:g}")
    return phrases


def build_prompt_context(bundle: EvidenceBundle) -> dict:
    """The ONLY facts the narrative provider is allowed to see."""

    current = bundle.derived.current_metrics
    previous = bundle.derived.previous_metrics
    return {
        "insight_id": bundle.insight_id,
        "team": bundle.team_id,
        "window": f"{bundle.window_start_minute:.0f}-{bundle.window_end_minute:.0f} minutes",
        "signals": describe_signals(bundle),
        "metrics": {
            "control_score_before": previous.control_score,
            "control_score_after": current.control_score,
            "final_third_entries_before": previous.final_third_entries,
            "final_third_entries_after": current.final_third_entries,
            "shots_before": previous.shots,
            "shots_after": current.shots,
            "recoveries_before": previous.recoveries,
            "recoveries_after": current.recoveries,
            "possession_before": previous.possession_share,
            "possession_after": current.possession_share,
        },
        "confidence": bundle.derived.confidence,
        "event_count": len(bundle.observed.event_ids),
        "constraints": (
            "Use only the metrics above. Do not mention players, formations, "
            "fatigue, injuries, tactics, scores, or league context."
        ),
        "allowed_terms": sorted(ALLOWED_FOOTBALL_TERMS),
    }


SYSTEM_PROMPT = (
    "You write short football broadcast analysis. You may only describe the "
    "provided statistics. Never invent players, scores, formations, tactics, "
    "fatigue or causes. If the evidence is weak, say the shift is not yet clear."
)
