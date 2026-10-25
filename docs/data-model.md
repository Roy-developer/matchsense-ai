# Data model

## Event

One validated event on a 100×100 pitch. Both teams attack towards `x = 100`, so
no coordinate flipping is needed anywhere.

| Field | Type | Notes |
|---|---|---|
| `event_id` | `EVT-####` | unique, ascending with the clock |
| `match_id` | string | a file may hold only one match |
| `period` | 1–5 | 1 = first half, 2 = second half |
| `minute` | 0–120 | **match-global** clock, so half 2 runs 45–90 |
| `second` | 0–59 | |
| `team_id` | `HOME` / `AWAY` | must match the player prefix |
| `player_id` | `HOME-##` / `AWAY-##` | |
| `event_type` | pass, shot, tackle, possession_change, pressure, foul | |
| `outcome` | type-dependent | see below |
| `start_x`, `start_y` | 0–100 | required |
| `end_x`, `end_y` | 0–100 | required for `pass` and `shot`, forbidden otherwise |
| `possession_id` | `POS-####` | must not change team |
| `play_pattern` | open_play, counterattack, set_piece, transition, press | |

Outcome vocabulary by type:

* `pass` → `successful` / `unsuccessful`
* `shot` → `goal` / `saved` / `blocked` / `off_target`
* `tackle`, `pressure`, `foul` → `successful` / `unsuccessful` / `won` / `lost`
* `possession_change` → `won` / `lost`

### The clock

`match_clock_seconds(period, minute, second) = minute * 60 + second`.

Because `minute` already contains elapsed match time, **no per-period offset may
be added**. Adding 45 minutes for the second half double-counts the interval and
pushes every second-half event past full time. This is enforced by regression
tests in `tests/unit/test_event_model.py`.

## Windows

A window is 300 simulated seconds. For an end point `E`, the current window is
`[E-300, E)` and the previous is `[E-600, E-300)`. Metrics are computed per team;
the opponent's window is computed separately so possession shares sum to 1.

## Detection

```json
{
  "insight_id": "INS-004",
  "team_id": "HOME",
  "start_minute": 55,
  "end_minute": 60,
  "control_score_delta": 0.27,
  "confidence": 0.83,
  "triggered_signal_names": ["final_third_entries", "shots", "possession_share"],
  "supporting_event_ids": ["EVT-0231", "..."],
  "algorithm_version": "control-shift-v1"
}
```

A detection requires **all** of: control-score delta above threshold, at least
two triggered signals, a minimum window activity, a non-empty baseline window,
and no detection for that team inside the cooldown period.

## Evidence Bundle

| Section | Contents | Rule |
|---|---|---|
| `observed` | event counts and event IDs in the window | directly reproducible |
| `derived` | before/after metrics, deltas, confidence breakdown | formula reproducible |
| `detector` | config, triggered signals, version, cooldown | thresholds captured |
| `interpreted` | claim, significance, critic decision | **starts empty** |
| `verification_status` | pending / approved / rejected | controlled by verification |
