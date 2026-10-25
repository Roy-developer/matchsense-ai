"""The full pipeline: MATCH-001 -> evidence bundles -> verified narrative (F-006).

This is the single source of truth used by the CLI, the API and the dashboard,
so the demo, the tests and the UI can never disagree.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from src.explainability.evidence import build_evidence_bundle, evidence_receipt
from src.explainability.provenance import is_bundle_grounded, provenance_chain
from src.intelligence.detector import ControlShiftDetector
from src.models.event import Event, MatchMeta
from src.models.insight import (
    Detection,
    DetectorConfig,
    EvidenceBundle,
    NarrativeOutput,
    VerificationResult,
    VerifiedClaim,
)
from src.narrative.pipeline import produce_narrative, resolve_claim
from src.narrative.provider import NarrativeProvider, get_provider

logger = logging.getLogger("matchsense.pipeline")


@dataclass
class InsightRun:
    """Everything produced for one detection, including the rejected cases."""

    detection: Detection
    bundle: EvidenceBundle
    candidates: list[tuple[str, str]] = field(default_factory=list)
    critic_decision: str = "pending"
    critic_reason: str = ""
    rejected_claim: str | None = None
    verified: VerifiedClaim | None = None
    verification: VerificationResult | None = None
    narratives: dict[str, NarrativeOutput] = field(default_factory=dict)

    @property
    def receipt(self) -> dict:
        return evidence_receipt(self.bundle)


@dataclass
class MatchRun:
    match_id: str
    meta: MatchMeta
    events: list[Event]
    insights: list[InsightRun] = field(default_factory=list)
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    provider: str = "template"

    @property
    def approved(self) -> list[InsightRun]:
        return [run for run in self.insights if run.verified is not None]

    def summary(self) -> dict:
        return {
            "match_id": self.match_id,
            "home_team": self.meta.home_team,
            "away_team": self.meta.away_team,
            "score": f"{self.meta.home_goals}-{self.meta.away_goals}",
            "events": len(self.events),
            "detections": len(self.insights),
            "approved": len(self.approved),
            "rejected": len(self.insights) - len(self.approved),
            "provider": self.provider,
            "correlation_id": self.correlation_id,
        }


def run_pipeline(
    events: list[Event],
    meta: MatchMeta,
    *,
    provider: NarrativeProvider | None = None,
    config: DetectorConfig | None = None,
    audiences: tuple[str, ...] = ("fan", "analyst", "broadcast"),
    max_insights: int | None = None,
) -> MatchRun:
    """Deterministic analytics first; AI only expresses what survived criticism."""

    config = config or DetectorConfig()
    provider = provider or get_provider()
    run = MatchRun(match_id=meta.match_id, meta=meta, events=events, provider=provider.name)

    detections = ControlShiftDetector(config).detect(events, meta.match_id)
    if max_insights is not None:
        detections = detections[:max_insights]

    for detection in detections:
        bundle = build_evidence_bundle(detection, events, config)

        if not is_bundle_grounded(bundle, events):
            logger.warning(
                "dropping ungrounded bundle insight=%s match=%s stage=evidence",
                bundle.insight_id,
                meta.match_id,
            )
            continue

        insight = InsightRun(detection=detection, bundle=bundle)

        # 1. Interpretation Agent proposes meaning from facts only.
        claim, significance = provider.interpret(bundle)
        insight.candidates.append((claim, significance))
        bundle.interpreted.claim = claim
        bundle.interpreted.significance = significance

        # 2. Critic + deterministic verification resolve the claim.
        verified, verification = resolve_claim(bundle, claim, significance)
        insight.verification = verification
        if verified is None:
            insight.critic_decision = "reject"
            insight.critic_reason = "; ".join(verification.reasons)
            insight.rejected_claim = claim
            bundle.interpreted.critic_decision = "reject"
            bundle.interpreted.critic_reason = insight.critic_reason
            bundle.interpreted.rejected_claim = claim
            bundle.verification_status = "rejected"
            run.insights.append(insight)
            continue

        # 3. Narrative Agent expresses only the approved claim.
        insight.critic_decision = "accept"
        insight.verified = verified
        bundle.interpreted.critic_decision = "accept"
        bundle.verification_status = "approved"

        for audience in audiences:
            output, narrative_check = produce_narrative(verified, bundle, provider, audience)
            if output is not None:
                insight.narratives[audience] = output
            elif narrative_check.reasons:
                logger.warning(
                    "narration rejected insight=%s audience=%s reasons=%s",
                    verified.insight_id,
                    audience,
                    narrative_check.reasons,
                )

        run.insights.append(insight)

    return run


def run_pipeline_from_dir(
    data_dir: str | Path, match_id: str = "MATCH-001", **kwargs
) -> MatchRun:
    from src.data.loader import load_match

    events, meta, validation = load_match(data_dir, match_id)
    if not validation.valid:
        raise ValueError(f"match {match_id} failed validation: {validation.errors}")
    return run_pipeline(events, meta, **kwargs)


def receipt_payload(run: MatchRun) -> list[dict]:
    """Evidence Receipt rows for the UI, including the rejected claim."""

    rows = []
    for insight in run.insights:
        receipt = insight.receipt
        receipt["critic"] = {
            "decision": insight.critic_decision,
            "reason": insight.critic_reason,
            "rejected_claim": insight.rejected_claim,
        }
        receipt["verified_claim"] = insight.verified.claim if insight.verified else None
        receipt["provenance"] = provenance_chain(insight.bundle, run.events)
        rows.append(receipt)
    return rows
