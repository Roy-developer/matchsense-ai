"""Narrative provider abstraction (AI-001).

The template provider is the default and requires no credentials, so the demo
always works offline. An Azure OpenAI provider can be swapped in without any
change upstream - but it gets exactly the same constrained facts.
"""

from __future__ import annotations

import os
from typing import Protocol

from src.models.insight import EvidenceBundle, VerifiedClaim
from src.narrative.prompts import build_prompt_context, describe_signals

# Percentages read better than raw ratios in broadcast prose.
PERCENT_SIGNALS = {"possession_share": "share of possession"}


class NarrativeProvider(Protocol):
    name: str

    def interpret(self, bundle: EvidenceBundle) -> tuple[str, str]:
        """Propose (claim, significance) from the bundle's facts only."""

    def narrate(self, claim: VerifiedClaim, audience: str) -> tuple[str, str]:
        """Express an already-verified claim for one audience."""


def _format_value(name: str, value: float) -> str:
    if name in PERCENT_SIGNALS:
        return f"{value * 100:.0f}%"
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{value:g}"


def _signal_phrase(name: str, previous: float, current: float) -> str:
    label = PERCENT_SIGNALS.get(name, name.replace("_", " "))
    if previous ==0 and current > 0:
        # Avoid "rising from 0 to ..." which reads like broken data.
        return f"{label} appearing where there was none"
    return f"{label} moving from {_format_value(name, previous)} to {_format_value(name, current)}"


class TemplateProvider:
    """Deterministic, offline, credential-free provider."""

    name = "template"

    def interpret(self, bundle: EvidenceBundle) -> tuple[str, str]:
        signals = [
            _signal_phrase(s.name, s.previous_value, s.current_value)
            for s in bundle.detector.triggered_signals
        ]
        window = f"{bundle.window_start_minute:.0f}-{bundle.window_end_minute:.0f}"
        side = "Home" if bundle.team_id == "HOME" else "Away"

        if not signals:
            return (
                f"No clear change for the {side} side in this window",
                "The underlying metrics did not move enough to support a claim.",
            )

        summary = signals[0]
        extra = ""
        if len(signals) > 1:
            zero_based = "appearing where there was none" in summary
            second_is_zero = "appearing where there was none" in signals[1]
            if zero_based and second_is_zero:
                # Both signals emerged from nothing; do not repeat the phrase.
                extra = f" and {len(signals)} independent signals moving together"
            else:
                extra = f", alongside {signals[1]}"
        claim = f"{side} side took control between {window} minutes with {summary}{extra}"
        significance = (
            f"The control score moved from "
            f"{bundle.derived.previous_metrics.control_score:.2f} to "
            f"{bundle.derived.current_metrics.control_score:.2f}, so the change is "
            f"carried by more than one metric rather than a single incident."
        )
        return claim, significance

    def narrate(self, claim: VerifiedClaim, audience: str) -> tuple[str, str]:
        window = claim.window or "this window"
        confidence = f"{claim.confidence:.2f}"

        if audience == "fan":
            return (
                "Momentum has swung",
                f"{claim.claim}. It is not one moment - several parts of the game moved together.",
            )
        if audience == "broadcast":
            return ("Control shift", f"{claim.claim}.")
        return (
            "Control shift detected",
            f"{claim.claim}. Window {window} minutes. "
            f"Control score {claim.metrics.get('control_score_before', 0):.2f} to "
            f"{claim.metrics.get('control_score_after', 0):.2f}. "
            f"Detector confidence {confidence}.",
        )


class AzureOpenAIProvider:
    """Optional provider. Kept thin: the demo never depends on it being reachable."""

    name = "azure_openai"

    def __init__(self, endpoint: str, api_key: str, deployment: str, api_version: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version

    def interpret(self, bundle: EvidenceBundle) -> tuple[str, str]:
        context = build_prompt_context(bundle)
        from src.narrative.client import request_json

        payload = request_json(self, context)
        return payload["claim"], payload["significance"]

    def narrate(self, claim: VerifiedClaim, audience: str) -> tuple[str, str]:
        from src.narrative.client import request_narrative

        payload = request_narrative(self, claim, audience)
        return payload["headline"], payload["body"]


def get_provider() -> "NarrativeProvider":
    """Select a provider from the environment, defaulting to the safe one."""

    choice = os.getenv("MATCHSENSE_NARRATIVE_PROVIDER", "template").strip().lower()
    if choice == "azure_openai":
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        if endpoint and api_key and deployment:
            return AzureOpenAIProvider(endpoint, api_key, deployment, api_version)
        # A misconfigured cloud provider must never break the demo.
    return TemplateProvider()
