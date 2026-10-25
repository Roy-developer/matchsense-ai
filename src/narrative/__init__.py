"""Narrative layer: prompts, provider abstraction, guardrails and verification."""

from src.narrative.pipeline import grounding_errors, produce_narrative, resolve_claim
from src.narrative.provider import NarrativeProvider, TemplateProvider, get_provider

__all__ = [
    "NarrativeProvider",
    "TemplateProvider",
    "get_provider",
    "grounding_errors",
    "produce_narrative",
    "resolve_claim",
]
