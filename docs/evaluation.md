# Evaluation

## Quality gates

| Layer | What is tested | Gate |
|---|---|---|
| Data | schema, coordinates, ordering, unique IDs, team/player consistency | `test_event_model.py`, `test_generator.py` |
| Clock | period-2 mapping | `test_match_clock_seconds`, regression test |
| Analytics | counts, completion, progression, windows, determinism | `test_windows.py` |
| Detector | positive, negative, threshold, cooldown, confidence bounds | `test_detector.py` |
| Evidence | grounding, provenance, window containment | `test_pipeline.py` |
| AI | schema, invented numbers, insufficient evidence | `test_pipeline.py` |
| Critic | formation, fatigue, invented-number cases | `test_pipeline.py` |
| Personalisation | three audiences, identical facts | `test_pipeline.py` |
| Resilience | sparse match, empty match, provider fallback | `test_pipeline.py` |

## Running

```powershell
pytest -q
```

Current status: **78 tests passing.**

## Golden behaviour

MATCH-001 with seed `20261023` reproduces byte-identically. The generator test
asserts:

* identical event lists for the same seed, different for another seed;
* every five-minute window of the match contains events;
* the scoreline stays believable (1–8 goals, 6–40 shots);
* the scripted 55–68' home pressure spell and the counterattack passages exist.

The pipeline test asserts the same detections and the same claims across runs.

## Known limitations

* Synthetic data only; the shot-quality proxy is a documented heuristic, not xG.
* Control score weights are a design choice, configurable in `DetectorConfig`.
* Confidence measures detector strength, not probability of football truth.
* One detector type (`control_shift`); counterattack and defensive-instability
  detectors are roadmap items.
