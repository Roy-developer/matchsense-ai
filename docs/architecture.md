# Architecture

## Pipeline

```
JSONL events → Pydantic validation → replay / match state
             → rolling windows (current 300s vs previous 300s)
             → control-shift detector (multi-signal + cooldown)
             → evidence bundle (observed / derived / interpreted)
             → interpretation agent (facts only)
             → critic + deterministic verification
             → verified claim
             → narrative agent (fan / analyst / broadcast)
             → dashboard + API
```

## Module map

| Path | Responsibility |
|---|---|
| `src/models/event.py` | Canonical typed event; clock mapping `match_clock_seconds` |
| `src/models/insight.py` | Window metrics, detection, evidence bundle, verified claim, narrative |
| `src/data/generator.py` | Seeded synthetic match with scripted scenarios |
| `src/data/validator.py` | Match-level checks: uniqueness, ordering, possession continuity |
| `src/data/loader.py` | JSONL + metadata loading with error line numbers |
| `src/features/metrics.py` | Pure football predicates (progressive, final third, threat proxy) |
| `src/features/windows.py` | Window bounds, metric computation, comparison |
| `src/intelligence/detector.py` | Signals, thresholds, confidence, cooldown |
| `src/intelligence/rules.py` | Baseline and meaningful-change guards |
| `src/explainability/evidence.py` | Bundle construction and Evidence Receipt |
| `src/explainability/provenance.py` | Event-ID traceability checks |
| `src/explainability/adversarial.py` | Claims that must be rejected (demo) |
| `src/narrative/prompts.py` | Allowed vocabulary, blocked phrases, prompt context |
| `src/narrative/provider.py` | Template (default) and Azure OpenAI providers |
| `src/narrative/guardrails.py` | Deterministic critique of unsupported content |
| `src/narrative/pipeline.py` | Claim resolution, verification, narrative production |
| `src/pipeline.py` | End-to-end orchestration used by CLI, API and UI |
| `src/api/main.py` | FastAPI contract |
| `src/ui/app.py` | Streamlit dashboard |

## Design decisions

**The LLM never computes a number.** All figures come from `src/features` and
`src/intelligence`. The narrative layer only receives pre-computed facts.

**Truth is layered.** `Observed` (counted events), `Derived` (documented
formulas), `Interpreted` (agent prose). The label travels with the claim.

**Interpretation starts empty.** `EvidenceBundle.interpreted` is populated only
after the Critic decides, so an unverified claim can never be mistaken for fact.

**Confidence is algorithmic, not probabilistic.** It combines signal strength,
multi-metric agreement, persistence and sample sufficiency. It is a measure of
how strongly the detector fired, not a calibrated probability of football truth.

**Windows compare against a real baseline.** The first five minutes are skipped
because the preceding window is empty; otherwise the start of the match would
manufacture a false "shift".

## Failure behaviour

| Failure | Behaviour |
|---|---|
| Empty or sparse match | Pipeline returns zero or few insights; UI states clearly |
| Azure OpenAI unreachable | `get_provider()` falls back to the template provider |
| Narrative rejected | Recorded with a reason; no card is rendered |
| Ungrounded bundle | Dropped with a warning log before reaching the UI |
