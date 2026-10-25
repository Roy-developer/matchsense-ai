# Explainability

## The three truth layers

| Layer | Definition | Examples | Produced by |
|---|---|
| **Observed** | stored or counted directly from source events | event IDs, passes, shots, recoveries | event stream + counting |
| **Derived** | calculated from observed facts by documented formula | completion %, progressive passes, control score, confidence | analytics code |
| **Interpreted** | meaning proposed in natural language | "Home side took control between 55-60 minutes" | interpretation agent, pending criticism |

A label follows its claim through the whole pipeline. An interpreted statement is
never stored or displayed as an observed fact, and heuristic quantities are
labelled as engineered rather than official statistics.

## The Evidence Receipt

Every published insight answers *"Why did MatchSense say this?"* with:

1. the exact five-minute window, in both minutes and seconds;
2. the event IDs inside it, with player, type and outcome;
3. metric values before and after, plus the deltas;
4. the confidence score **and** its four-part breakdown;
5. which signals exceeded which thresholds;
6. the detector and data versions;
7. the Critic's decision, including any rejected claim and the reason.

Nothing in the receipt is generated text.

## What the Critic blocks

The Critic is deterministic, so its behaviour is testable without a model.

| Category | Example | Reason recorded |
|---|---|---|
| Unsupported context | "switched to a 4-3-3" | the formation is not in the event data |
| Invented numbers | "97 percent possession" | the number does not appear in the evidence |
| Unobservable states | "visibly tired", "injured" | fatigue and injury are not event attributes |
| Vague claims | no triggered signals | nothing supports the statement |

Numbers are compared against evidence values with a tolerance that permits the
rounding used in prose, so a legitimate `0.589 → 0.59` is accepted while an
invented `97` is refused.

## Provenance checks

`is_bundle_grounded()` rejects a bundle whose cited event IDs do not exist or
fall outside its own window. `produce_narrative()` re-checks every event and
insight ID quoted in generated prose, so a narrative cannot cite evidence that
was not approved for that insight.

## Why this is not decorative

The guide's requirement is that the system can *refuse* a conclusion. That is
only meaningful if refusal is observable, so the dashboard includes a
"Critic check" panel that attempts three unsupported claims on every run and
shows the rejection reason for each one.
