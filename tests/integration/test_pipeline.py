"""Integration: generate -> validate -> detect -> evidence -> verify -> narrative.

Also covers the failure paths the guide requires: sparse matches, an unreachable
LLM, and an interpretation that must be rejected by the Critic.
"""

from __future__ import annotations

from src.data.generator import build_match
from src.data.loader import load_match
from src.data.validator import validate_events
from src.explainability.provenance import is_bundle_grounded
from src.models.event import Event
from src.narrative.pipeline import produce_narrative, resolve_claim
from src.narrative.provider import TemplateProvider, get_provider
from src.pipeline import receipt_payload, run_pipeline
from src.data.generator import write_match


def test_end_to_end_pipeline_approves_claims(golden_models):
    events, meta = None, None
    records, meta = build_match()
    events = [Event(**record) for record in records]

    run = run_pipeline(events, meta)
    assert run.insights
    assert run.approved
    for insight in run.approved:
        assert insight.verified is not None
        assert insight.verified.verification_status == "approved"
        assert insight.verified.evidence_refs == [insight.detection.insight_id]
        assert insight.narratives, "an approved claim must yield narratives"


def test_every_bundle_is_grounded_in_events(golden_models_records=None):
    records, meta = build_match()
    events = [Event(**record) for record in records]
    run = run_pipeline(events, meta)
    for insight in run.insights:
        assert is_bundle_grounded(insight.bundle, events)
        assert insight.bundle.interpreted.critic_decision in {"accept", "reject"}


def test_pipeline_is_deterministic():
    records, meta = build_match()
    events = [Event(**record) for record in records]
    first = run_pipeline(events, meta)
    second = run_pipeline(events, meta)
    assert [i.receipt for i in first.insights] == [i.receipt for i in second.insights]
    assert [i.verified.claim if i.verified else None for i in first.insights] == [
        i.verified.claim if i.verified else None for i in second.insights
    ]


def test_audiences_share_the_same_verified_facts():
    records, meta = build_match()
    events = [Event(**record) for record in records]
    run = run_pipeline(events, meta)
    for insight in run.approved:
        bodies = {audience: narrative.body for audience, narrative in insight.narratives.items()}
        assert len(bodies) == 3
        for narrative in insight.narratives.values():
            assert narrative.evidence_refs == insight.verified.evidence_refs
            assert narrative.insight_id == insight.verified.insight_id


def test_critic_rejects_unsupported_formation_claim():
    records, meta = build_match()
    events = [Event(**record) for record in records]
    run = run_pipeline(events, meta, max_insights=1)
    bundle = run.insights[0].bundle

    claim = "The home side switched to a 4-3-3 formation and pressed higher"
    verified, result = resolve_claim(bundle, claim, "This change explains the momentum.")

    assert verified is None
    assert result.status == "rejected"
    assert any("unsupported context" in reason for reason in result.reasons)


def test_critic_rejects_invented_numbers():
    records, meta = build_match()
    events = [Event(**record) for record in records]
    run = run_pipeline(events, meta, max_insights=1)
    bundle = run.insights[0].bundle

    claim = "The home side had 97 percent possession and 42 shots in this spell"
    verified, result = resolve_claim(bundle, claim, "Complete control.")
    assert verified is None
    assert any("unsupported number" in reason for reason in result.reasons)


def test_unapproved_claim_cannot_be_narrated():
    records, meta = build_match()
    events = [Event(**record) for record in records]
    run = run_pipeline(events, meta, max_insights=1)
    bundle = run.insights[0].bundle
    verified, _ = resolve_claim(bundle, "Claim", "Significance")
    assert verified is not None

    revoked = verified.model_copy(update={"verification_status": "rejected"})
    output, result = produce_narrative(revoked, bundle, TemplateProvider(), "fan")
    assert output is None
    assert not result.accepted


def test_sparse_match_is_handled():
    records, meta = build_match()
    events = [Event(**record) for record in records[:15]]
    result = validate_events(events)
    assert result.warnings

    run = run_pipeline(events, meta)
    assert isinstance(run.summary()["approved"], int)


def test_empty_match_is_handled():
    records, meta = build_match()
    run = run_pipeline([], meta)
    assert run.summary()["detections"] == 0
    assert receipt_payload(run) == []


def test_provider_falls_back_when_azure_is_misconfigured(monkeypatch):
    monkeypatch.setenv("MATCHSENSE_NARRATIVE_PROVIDER", "azure_openai")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    assert get_provider().name == "template"


def test_demo_slice_from_disk(tmp_path):
    write_match(tmp_path)
    events, meta, validation = load_match(tmp_path)
    assert validation.valid

    run = run_pipeline(events, meta)
    receipts = receipt_payload(run)
    assert receipts
    for receipt in receipts:
        assert receipt["truth_layers"]["observed"]["event_ids"]
        assert receipt["truth_layers"]["derived"]["confidence"] >= 0
