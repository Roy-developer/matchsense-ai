"""Insight, evidence and narrative contracts (Guide v2 sections 8-10).

Every object here carries an explicit truth label so the UI can never show an
interpreted statement as an observed fact.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TruthLayer = Literal["observed", "derived", "interpreted"]
VerificationStatus = Literal["pending", "approved", "rejected", "insufficient_evidence"]
Audience = Literal["fan", "analyst", "broadcast"]


# ---------------------------------------------------------------------------
# Window metrics (deterministic layer)
# ---------------------------------------------------------------------------
class WindowMetrics(BaseModel):
    """Metrics for one rolling window. Every value is source-derived."""

    model_config = {"extra": "forbid"}

    start_second: int
    end_second: int
    start_minute: float
    end_minute: float
    event_count: int

    passes_attempted: int = 0
    passes_completed: int = 0
    progressive_passes: int = 0
    final_third_entries: int = 0
    penalty_area_entries: int = 0
    shots: int = 0
    shots_on_target: int = 0
    goals: int = 0
    recoveries: int = 0
    presses: int = 0
    attacking_actions: int = 0
    counterattack_actions: int = 0
    threat_added: float = 0.0

    possession_share: float = 0.0
    pass_completion_pct: float = 0.0
    control_score: float = 0.0
    average_sequence_length: float = 0.0

    supporting_event_ids: list[str] = Field(default_factory=list)


class WindowComparison(BaseModel):
    """Current 5-minute window versus the immediately preceding one."""

    model_config = {"extra": "forbid"}

    team_id: Literal["HOME", "AWAY"]
    previous: WindowMetrics
    current: WindowMetrics

    possession_share_delta: float = 0.0
    progressive_passes_delta: int = 0
    final_third_entries_delta: int = 0
    shots_delta: int = 0
    threat_added_delta: float = 0.0
    recoveries_delta: int = 0
    presses_delta: int = 0
    attacking_actions_delta: int = 0
    control_score_delta: float = 0.0
    pass_completion_delta: float = 0.0


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
class DetectorConfig(BaseModel):
    """All thresholds are configuration, never hidden constants."""

    model_config = {"extra": "forbid"}

    weight_possession: float = 0.20
    weight_progressive: float = 0.15
    weight_final_third: float = 0.20
    weight_shots: float = 0.15
    weight_threat: float = 0.15
    weight_recoveries: float = 0.15

    control_score_threshold: float = 0.12
    minimum_signals: int = 2
    minimum_window_events: int = 6
    minimum_supporting_events: int = 3
    possession_signal_delta: float = 0.08
    progressive_signal_delta: int = 2
    final_third_signal_delta: int = 2
    shots_signal_delta: int = 1
    threat_signal_delta: float = 0.02
    recovery_signal_delta: int = 1

    persistence_windows: int = 2
    cooldown_seconds: int = 600


class Signal(BaseModel):
    """One independent supporting signal inside a detection."""

    model_config = {"extra": "forbid"}

    name: str
    metric: str
    previous_value: float
    current_value: float
    delta: float
    threshold: float
    triggered: bool
    truth_layer: TruthLayer = "derived"


class Detection(BaseModel):
    """Output of the control-shift detector, before any interpretation."""

    model_config = {"extra": "forbid"}

    insight_id: str
    match_id: str
    type: Literal["control_shift"] = "control_shift"
    team_id: Literal["HOME", "AWAY"]
    start_minute: float
    end_minute: float
    detected_at_second: int

    comparison: WindowComparison
    signals: list[Signal]
    triggered_signal_names: list[str]
    control_score_delta: float
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_breakdown: dict[str, float]
    supporting_event_ids: list[str]
    algorithm_version: str = "control-shift-v1"
    data_version: str = "synthetic-demo-v1"
    cooldown_until_second: int


# ---------------------------------------------------------------------------
# Evidence Bundle
# ---------------------------------------------------------------------------
class ObservedEvidence(BaseModel):
    model_config = {"extra": "forbid"}

    event_counts: dict[str, int]
    event_ids: list[str]
    truth_layer: TruthLayer = "observed"


class DerivedEvidence(BaseModel):
    model_config = {"extra": "forbid"}

    previous_metrics: WindowMetrics
    current_metrics: WindowMetrics
    deltas: dict[str, float]
    control_score_change: float
    confidence: float
    confidence_breakdown: dict[str, float]
    truth_layer: TruthLayer = "derived"


class DetectorEvidence(BaseModel):
    model_config = {"extra": "forbid"}

    config: DetectorConfig
    triggered_signals: list[Signal]
    algorithm_version: str
    cooldown_metadata: dict[str, int]


class InterpretedEvidence(BaseModel):
    """Starts empty by design: only the agent workflow may fill it in."""

    model_config = {"extra": "forbid"}

    claim: str | None = None
    significance: str | None = None
    critic_decision: Literal["accept", "revise", "reject"] | None = None
    critic_reason: str | None = None
    rejected_claim: str | None = None
    truth_layer: TruthLayer = "interpreted"


class EvidenceBundle(BaseModel):
    """The factual shared state between the deterministic core and the AI layer."""

    model_config = {"extra": "forbid"}

    insight_id: str
    match_id: str
    team_id: Literal["HOME", "AWAY"]
    type: str
    window_start_second: int
    window_end_second: int
    window_start_minute: float
    window_end_minute: float
    observed: ObservedEvidence
    derived: DerivedEvidence
    detector: DetectorEvidence
    interpreted: InterpretedEvidence = Field(default_factory=InterpretedEvidence)
    verification_status: VerificationStatus = "pending"


# ---------------------------------------------------------------------------
# Verification + narrative
# ---------------------------------------------------------------------------
class VerifiedClaim(BaseModel):
    """The single approved master claim. Narratives may only restate this."""

    model_config = {"extra": "forbid"}

    insight_id: str
    match_id: str
    team_id: Literal["HOME", "AWAY"]
    claim: str
    significance: str
    confidence: float
    evidence_refs: list[str]
    metrics: dict[str, float]
    window: str = ""
    truth_layer: TruthLayer = "interpreted"
    verification_status: VerificationStatus


class NarrativeOutput(BaseModel):
    model_config = {"extra": "forbid"}

    insight_id: str
    audience: Audience
    headline: str
    body: str
    evidence_refs: list[str]
    uncertainty_note: str
    provider: str
    verification_status: VerificationStatus


class VerificationResult(BaseModel):
    model_config = {"extra": "forbid"}

    accepted: bool
    status: VerificationStatus
    reasons: list[str] = Field(default_factory=list)
    numeric_checks: int = 0
