# MatchSense AI

**Evidence-grounded football match intelligence.**
Analytics determines what happened. Evidence proves why it happened. The LLM explains it — without inventing facts.

Built for the Microsoft *Inside the Game* developer hackathon.

---

## The problem

Broadcast and streaming coverage generates statistics, but statistics alone do not
tell a story — and an LLM asked to "explain the match" will invent players,
formations, fatigue and tactics that nobody can verify. MatchSense AI separates
the two: **deterministic analytics establish what happened**, an interpretation
proposes what it means, a **Critic challenges the claim**, and only verifiable
claims are published.

## Target users

* **Broadcast / streaming producers** who need a verified talking point in seconds.
* **Analysts** who need a number they can trace back to specific events.
* **Fans** who want the story without the invention.

## What makes it different

| Common pattern | MatchSense AI |
|---|---|
| Events → metrics → story | Events → metrics → candidate claim → **criticism** → **verification** → story |
| Evidence panel | Observed / Derived / Interpreted truth layers |
| One-pass generation | Accepted, revised, rejected, or insufficient evidence |
| Audience templates | Personalisation **after** verification — style changes, facts do not |
| Opaque insight | Claim provenance from event IDs to final narrative |

The demo deliberately feeds the Critic claims it must block:

```
⛔ formation   "switched to a 4-3-3 and pushed their full-backs higher"
⛔ invented    "97 percent possession and 42 shots in this spell"
⛔ fatigue     "visibly tired after a demanding week"
```

All three are refused with an explicit reason.

## Architecture

```
match_001.jsonl  (synthetic, seeded, deterministic)
        │
        ▼  Pydantic validation  ─ event schema, ordering, possession continuity
   Replay / Match State
        │
        ▼  Rolling windows       ─ current 300s vs immediately previous 300s
   Deterministic analytics      ─ passes, progressive passes, final-third entries,
        │                         shots, recoveries, threat proxy, control score
        ▼  Control-Shift Detector ─ multi-signal, thresholded, cooldown-aware
   Evidence Bundle              ─ Observed | Derived | Detector | Interpreted(empty)
        │
        ▼  Interpretation Agent   ─ proposes meaning from facts only
   Critic → Claim Resolver      ─ reject unsupported context and numbers
        │
        ▼  Deterministic verification
   Verified Claim               ─ approved, traceable, one source of truth
        │
        ▼  Narrative Agent        ─ Fan / Analyst / Broadcast
   Dashboard + FastAPI
```

Every layer is a pure function of the layer above it, so the dashboard, the API,
the CLI and the tests cannot disagree.

## Quick start

```powershell
git clone https://github.com/Roy-developer/matchsense-ai
cd matchsense-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m scripts.generate_match      # regenerate the seeded match (optional)
python -m scripts.run_demo            # MATCH-001 -> detection -> verified receipt
pytest -q                             # full test suite
streamlit run src/ui/app.py           # dashboard
uvicorn src.api.main:app --reload     # API docs at /docs
```

No Azure credentials are required. The narrative provider defaults to the
deterministic template provider so the demo always runs offline.

## Example insight and evidence

```
INS-004  HOME  55-60'  confidence 0.83

OBSERVED   47 events in window (EVT-0231..EVT-0277)
DERIVED    control score 0.44 -> 0.71
SIGNALS    final_third_entries, shots, possession_share, threat
APPROVED   Home side took control between 55-60 minutes with final third
           entries moving from 4 to 10
  [fan      ] Momentum has swung - ... not one moment, several parts moved together
  [analyst  ] Control shift detected - control score 0.44 to 0.71, confidence 0.83
  [broadcast] Control shift - Home side took control between 55-60 minutes ...
```

The `Why?` panel in the dashboard shows the same data as an Evidence Receipt:
event IDs, before/after metrics, the confidence breakdown, the detector version
and the Critic's decision.

## Microsoft technologies

* **FastAPI + Uvicorn** — the replay/state/insight/evidence/personalisation contract.
* **Azure OpenAI / Microsoft Foundry** (optional) — structured narrative through
  a provider abstraction, with deterministic fallback when unavailable.
* **Azure Container Apps** — the intended deployment target (Dockerfile included).
* **Docker** — reproducible local build.

## Tests

```powershell
pytest -q
```

Coverage includes event schema and coordinate bounds, the match clock, generator
determinism, window/feature arithmetic, detector thresholds and cooldown,
confidence bounds, evidence grounding, Critic rejection cases, audience
consistency, provider fallback and sparse/empty matches.

## Security and privacy

* No secrets in the repository — only `.env.example`; `.env` is git-ignored.
* No credentials, tokens or prompts are logged.
* The container runs as a non-root user with pinned dependencies.
* No third-party or licensed match data is included.

## Synthetic data limitation

All matches are **synthetic and fictional** (Harbour Rovers v Ridgeway
Athletic). Expected-threat and shot-quality values are documented heuristics,
not calibrated models. Nothing here uses or claims official Premier League data.
The generator is seeded, so a fixed seed reproduces the same match, metrics,
detections, evidence and narrative input byte for byte.

## Roadmap

* Real event-feed adapter behind the same validation contract.
* Calibrated xG/xT using licensed historical data.
* Streaming replay with WebSocket updates.
* Richer pattern detectors (counterattack, defensive instability, key player).

## Official hackathon alignment

Built against the official brief: transform synthetic, football-realistic events
into explainable match intelligence, narratives and recaps for broadcast,
studio or streaming.

* Rules: https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md
* Repository: https://github.com/microsoft/insidethegamehackathon
* Reactor series: https://developer.microsoft.com/en-us/reactor/series/S-1709/

See `docs/` for architecture, data model, explainability, evaluation, the demo
guide and submission checklist.
