"""Explainability layer: evidence bundles and provenance."""

from src.explainability.adversarial import adversarial_demo
from src.explainability.evidence import build_evidence_bundle, evidence_receipt
from src.explainability.provenance import (
    events_outside_window,
    is_bundle_grounded,
    provenance_chain,
    unresolved_event_ids,
)

__all__ = [
    "adversarial_demo",
    "build_evidence_bundle",
    "evidence_receipt",
    "events_outside_window",
    "is_bundle_grounded",
    "provenance_chain",
    "unresolved_event_ids",
]
